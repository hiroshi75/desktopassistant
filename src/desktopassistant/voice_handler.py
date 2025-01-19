from vosk import Model, KaldiRecognizer
import pyaudio
import json
import threading
from queue import Queue
from typing import Optional

class VoiceHandler:
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
                        self.event_queue.put("open_chat")
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
