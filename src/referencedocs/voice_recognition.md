# 音声コマンド認識の方法


## ライブラリのインストール

```
pip install pyaudio vosk
```

## モデルファイル

以下からモデルをダウンロード

<https://alphacephei.com/vosk/models/vosk-model-small-ja-0.22.zip>

ダウンロードしたzipは展開して適切な場所に置く。
モデルは以下のようなディレクトリ構成

path/to/vosk-model-small-ja-0.22
 |
 ┣─ am
 ┣─ conf
 ┣─ graph
 ┣─ vector
 ┣─ README

## サンプルプログラム

```python
from vosk import Model, KaldiRecognizer
import pyaudio
import json
from queue import Queue
import threading

def listen_for_commands_offline(queue, stop_event):
    """オフライン音声認識 (Vosk)"""
    try:
        # モデルのロード
        model = Model("vosk-model-small-ja-0.22/vosk-model-small-ja-0.22")
        recognizer = KaldiRecognizer(model, 16000)

        # マイクの設定
        mic = pyaudio.PyAudio()
        stream = mic.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, frames_per_buffer=4096)
        stream.start_stream()

        print("Listening for commands (offline)...")
        while not stop_event.is_set():  # 停止イベントを監視
            data = stream.read(4096, exception_on_overflow=False)
            if recognizer.AcceptWaveform(data):
                result = json.loads(recognizer.Result())
                command = result.get("text", "")
                print(f"Recognized (offline): {command}")
                if "チャットを開いて" in command:
                    queue.put("open_chat")
                elif "終了" in command:
                    queue.put("quit")

    except KeyboardInterrupt:
        print("\nShutting down voice recognition...")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        stream.stop_stream()
        stream.close()
        mic.terminate()
        print("Voice recognition stopped.")

def manage_commands(queue, stop_event):
    """コマンドの処理"""
    try:
        while not stop_event.is_set():
            command = queue.get()
            if command == "open_chat":
                print("Opening chat window... (Here you can call your WebView logic)")
            elif command == "quit":
                print("Exiting application...")
                stop_event.set()  # 停止イベントを設定
                break
    except KeyboardInterrupt:
        print("\nExiting gracefully...")

if __name__ == "__main__":
    stop_event = threading.Event()
    command_queue = Queue()

    # 音声認識スレッドを起動
    listener_thread = threading.Thread(target=listen_for_commands_offline, args=(command_queue, stop_event), daemon=True)
    listener_thread.start()

    try:
        # メインスレッドでコマンド処理
        manage_commands(command_queue, stop_event)
    except KeyboardInterrupt:
        print("\nKeyboardInterrupt detected. Shutting down...")
        stop_event.set()  # 停止イベントを設定
        listener_thread.join()
        print("Application exited.")

```