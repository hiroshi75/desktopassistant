from vosk import Model, KaldiRecognizer
import pyaudio
import json
import threading
import asyncio
import websockets
import numpy as np
import time
from queue import Queue
from typing import Optional, Tuple

class VoiceHandler:
    # 静寂検出のための定数
    SILENCE_THRESHOLD = 500  # 静寂判定の閾値
    SILENCE_DURATION = 2.0   # 静寂判定の継続時間（秒）
    WEBSOCKET_URL = "ws://localhost:8001/TranscribeStreaming"  # WebSocketサーバーのURL

    def __init__(self, model_path: str, event_queue: Queue, simulation_mode: bool = False):
        """音声認識ハンドラーの初期化

        Args:
            model_path (str): Voskモデルのパス
            event_queue (Queue): イベントキュー（メインプロセスと共有）
            simulation_mode (bool): シミュレーションモードの有効/無効
        """
        self.model = Model(model_path)
        self.recognizer = KaldiRecognizer(self.model, 16000)
        self.event_queue = event_queue
        self.stop_event = threading.Event()
        self._stream: Optional[pyaudio.Stream] = None
        self._audio: Optional[pyaudio.PyAudio] = None
        self.simulation_mode = simulation_mode
        
        # シミュレーション用の音声データ
        if simulation_mode:
            self.simulation_data = [
                ("パスタを作って", 2.0),  # (テキスト, 待機時間)
                ("", 2.0),  # 静寂期間
            ]
            self.simulation_index = 0

    def _simulate_voice_input(self):
        """シミュレーションモードでの音声入力"""
        print("シミュレーションモードで実行中...")
        
        while not self.stop_event.is_set() and self.simulation_index < len(self.simulation_data):
            text, wait_time = self.simulation_data[self.simulation_index]
            if text:
                print(f"シミュレーション: 「{text}」を認識")
                if "パスタ" in text:
                    print("ウェイクワード'パスタ'を検出しました")
                    asyncio.run(self.stream_audio_to_server())
            else:
                print(f"シミュレーション: {wait_time}秒の静寂")
            
            time.sleep(wait_time)
            self.simulation_index += 1

    def start(self):
        """音声認識の開始"""
        if self.simulation_mode:
            self._simulate_voice_input()
            return

        try:
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
                            print("ウェイクワード'パスタ'を検出しました")
                            # WebSocketを使用して音声をストリーミング
                            asyncio.run(self.stream_audio_to_server())
                except IOError as e:
                    print(f"音声入力エラー: {e}")
                    break
                except Exception as e:
                    print(f"音声認識エラー: {e}")
                    break

        except Exception as e:
            print(f"音声デバイスの初期化エラー: {e}")
        finally:
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
        try:
            async with websockets.connect(
                self.WEBSOCKET_URL,
                ping_interval=20,
                ping_timeout=10,
                close_timeout=5,
                max_size=None
            ) as ws:
                self.event_queue.put(("status", "音声入力を開始しました"))

                if self.simulation_mode:
                    # シミュレーションモード: テスト用の音声データを生成して送信
                    try:
                        # 16ビット、16kHzのテスト音声データを生成（0.25秒分）
                        duration = 0.25  # 秒
                        samples = int(16000 * duration)
                        t = np.linspace(0, duration, samples, False)
                        # 440Hzの正弦波を生成（人間の声に近い周波数）
                        audio = np.sin(2 * np.pi * 440 * t)
                        # 16ビットの範囲（-32768から32767）にスケーリング
                        audio = (audio * 32767).astype(np.int16)
                        
                        # 音声データを3秒分送信（0.25秒ごと）
                        for i in range(12):  # 3秒 = 12 * 0.25秒
                            # 最初の1秒は通常の音声、その後は徐々に音量を下げる
                            if i >= 4:  # 1秒以降
                                fade_factor = max(0.1, 1.0 - (i - 4) * 0.2)  # 徐々に音量を下げる
                                audio_chunk = (audio * fade_factor).astype(np.int16)
                            else:
                                audio_chunk = audio
                            
                            await ws.send(audio_chunk.tobytes())
                            self.event_queue.put(("status", f"シミュレーション: 音声データ送信中 ({i * 0.25:.1f}秒)"))
                            await asyncio.sleep(0.25)
                        
                        # 終了シグナルを送信
                        await ws.send("submit_response")
                        self.event_queue.put(("status", "シミュレーション: 音声送信完了"))
                        
                        # サーバーからの応答を待機（最大5秒）
                        try:
                            async def wait_for_response():
                                async for message in ws:
                                    if isinstance(message, str):
                                        if message.startswith("認識テキスト:"):
                                            self.event_queue.put(("transcription", message[7:].strip()))
                                        elif message.startswith("応答:"):
                                            self.event_queue.put(("response", message[3:].strip()))
                                            return True
                                return False

                            await asyncio.wait_for(wait_for_response(), timeout=5.0)
                        except asyncio.TimeoutError:
                            self.event_queue.put(("error", "音声認識がタイムアウトしました"))
                        finally:
                            # 明示的にWebSocket接続を閉じる
                            await ws.close()
                            
                    except Exception as e:
                        error_msg = f"シミュレーション音声送信エラー: {e}"
                        print(error_msg)
                        self.event_queue.put(("error", error_msg))
                        try:
                            await ws.close()
                        except:
                            pass
                
                else:
                    # 通常モード: 実際の音声デバイスを使用
                    stream = None
                    audio = None
                    try:
                        audio = pyaudio.PyAudio()
                        stream = audio.open(
                            format=pyaudio.paInt16,
                            channels=1,
                            rate=16000,
                            input=True,
                            frames_per_buffer=4096
                        )
                        stream.start_stream()

                        silence_start = None
                        while True:
                            try:
                                data = stream.read(4096, exception_on_overflow=False)
                                
                                if self.detect_silence(data):
                                    if silence_start is None:
                                        silence_start = asyncio.get_event_loop().time()
                                    elif asyncio.get_event_loop().time() - silence_start >= self.SILENCE_DURATION:
                                        self.event_queue.put(("status", "静寂を検出しました"))
                                        # 最後の音声データを送信
                                        await ws.send(data)
                                        # 終了シグナルを送信
                                        await ws.send("submit_response")
                                        # 音声認識結果を待機（最大5秒）
                                        # 音声認識結果を待機（最大5秒）
                                        try:
                                            async def wait_for_response():
                                                async for message in ws:
                                                    if isinstance(message, str):
                                                        if message.startswith("認識テキスト:"):
                                                            self.event_queue.put(("transcription", message[7:].strip()))
                                                        elif message.startswith("応答:"):
                                                            self.event_queue.put(("response", message[3:].strip()))
                                                            return True
                                                return False

                                            await asyncio.wait_for(wait_for_response(), timeout=5.0)
                                        except asyncio.TimeoutError:
                                            self.event_queue.put(("error", "音声認識がタイムアウトしました"))
                                        break
                                else:
                                    silence_start = None

                                await ws.send(data)

                            except IOError as e:
                                print(f"音声データの読み取りエラー: {e}")
                                break

                    finally:
                        if stream:
                            stream.stop_stream()
                            stream.close()
                        if audio:
                            audio.terminate()

                # サーバーからの応答を待機
                self.event_queue.put(("status", "サーバーからの応答を待機中"))
                async for message in ws:
                    if isinstance(message, str):
                        if message.startswith("認識テキスト:"):
                            self.event_queue.put(("transcription", message[7:].strip()))
                        elif message.startswith("応答:"):
                            self.event_queue.put(("response", message[3:].strip()))
                        elif message.startswith("最終認識テキスト:"):
                            self.event_queue.put(("final_transcription", message[10:].strip()))
                        else:
                            self.event_queue.put(("server_message", message))

        except Exception as e:
            error_msg = f"音声ストリーミングエラー: {e}"
            print(error_msg)
            self.event_queue.put(("error", error_msg))
