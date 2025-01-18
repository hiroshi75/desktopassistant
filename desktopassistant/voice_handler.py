from vosk import Model, KaldiRecognizer
import pyaudio
import json
import threading
import asyncio
import websockets
import numpy as np
from queue import Queue
from typing import Optional, Tuple

class VoiceHandler:
    # 静寂検出のための定数
    SILENCE_THRESHOLD = 500  # 静寂判定の閾値
    SILENCE_DURATION = 2.0   # 静寂判定の継続時間（秒）
    WEBSOCKET_URL = "ws://localhost:8001/TranscribeStreaming"  # WebSocketサーバーのURL

    def __init__(self, model_path: str, event_queue: Queue):
        """音声認識ハンドラーの初期化

        Args:
            model_path (str): Voskモデルのパス
            event_queue (Queue): イベントキュー（メインプロセスと共有）
        """
        self.model = Model(model_path)
        self.recognizer = KaldiRecognizer(self.model, 16000)
        self.event_queue = event_queue
        self.stop_event = threading.Event()
        self._stream: Optional[pyaudio.Stream] = None
        self._audio: Optional[pyaudio.PyAudio] = None

    def start(self):
        """音声認識の開始"""
        self._audio = pyaudio.PyAudio()
        self._stream = self._audio.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=16000,
            input=True,
            frames_per_buffer=4096
        )
        self._stream.start_stream()

        while not self.stop_event.is_set():
            try:
                data = self._stream.read(4096, exception_on_overflow=False)
                if self.recognizer.AcceptWaveform(data):
                    result = json.loads(self.recognizer.Result())
                    text = result.get("text", "")
                    if "パスタ" in text:
                        # WebSocketを使用して音声をストリーミング
                        asyncio.run(self.stream_audio_to_server())
            except Exception as e:
                print(f"Error during voice recognition: {e}")
                break

        self.stop()

    def stop(self):
        """音声認識の停止とリソースのクリーンアップ"""
        self.stop_event.set()
        if self._stream:
            self._stream.stop_stream()
            self._stream.close()
            self._stream = None
        if self._audio:
            self._audio.terminate()
            self._audio = None

    def start_background(self):
        """バックグラウンドスレッドでの音声認識開始"""
        self.stop_event.clear()
        thread = threading.Thread(target=self.start, daemon=True)
        thread.start()
        return thread

    def detect_silence(self, audio_data: bytes) -> bool:
        """音声データから静寂を検出する

        Args:
            audio_data (bytes): 音声データ（16ビット整数のバイト列）

        Returns:
            bool: 静寂であればTrue
        """
        # バイト列を16ビット整数の配列に変換
        audio_array = np.frombuffer(audio_data, dtype=np.int16)
        # 振幅の平均値を計算
        amplitude = np.abs(audio_array).mean()
        return amplitude < self.SILENCE_THRESHOLD

    async def stream_audio_to_server(self):
        """音声をWebSocketサーバーにストリーミングする"""
        stream = None
        audio = None
        try:
            # 新しい音声ストリームを作成（サーバー要件に合わせて8000Hz）
            audio = pyaudio.PyAudio()
            stream = audio.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=16000,
                input=True,
                frames_per_buffer=4096
            )
            stream.start_stream()

            async with websockets.connect(self.WEBSOCKET_URL) as ws:
                silence_start = None
                self.event_queue.put(("status", "音声入力を開始しました"))

                while True:
                    try:
                        # 音声データの読み取り
                        data = stream.read(4096, exception_on_overflow=False)
                        
                        # 静寂検出
                        if self.detect_silence(data):
                            if silence_start is None:
                                silence_start = asyncio.get_event_loop().time()
                            elif asyncio.get_event_loop().time() - silence_start >= self.SILENCE_DURATION:
                                # 2秒以上の静寂を検出
                                await ws.send("submit_response")
                                self.event_queue.put(("status", "静寂を検出しました"))
                                break
                        else:
                            silence_start = None

                        # 音声データの送信
                        await ws.send(data)

                    except IOError as e:
                        print(f"音声データの読み取りエラー: {e}")
                        break

                # サーバーからの応答を待機
                self.event_queue.put(("status", "サーバーからの応答を待機中"))
                async for message in ws:
                    if isinstance(message, str):
                        # メッセージの種類に基づいて処理
                        if message.startswith("認識テキスト:"):
                            self.event_queue.put(("transcription", message[7:].strip()))
                        elif message.startswith("応答:"):
                            self.event_queue.put(("response", message[3:].strip()))
                        elif message.startswith("最終認識テキスト:"):
                            self.event_queue.put(("final_transcription", message[10:].strip()))
                        else:
                            # その他のメッセージ（エラーなど）
                            self.event_queue.put(("server_message", message))

        except Exception as e:
            error_msg = f"音声ストリーミングエラー: {e}"
            print(error_msg)
            self.event_queue.put(("error", error_msg))

        finally:
            # リソースのクリーンアップ
            if stream:
                stream.stop_stream()
                stream.close()
            if audio:
                audio.terminate()
