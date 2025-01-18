import webview
import threading
from pystray import Icon, Menu, MenuItem
from PIL import Image, ImageDraw
from queue import Queue
import os

# HTMLのテンプレート
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>デスクトップアシスタント</title>
    <style>
        body {
            font-family: 'Hiragino Sans', 'Meiryo', sans-serif;
            margin: 0;
            padding: 0;
            display: flex;
            flex-direction: column;
            height: 100vh;
            background-color: #f0f0f0;
        }
        #chat {
            flex: 1;
            padding: 10px;
            overflow-y: auto;
            background: #ffffff;
            border-bottom: 1px solid #ddd;
        }
        #input-container {
            display: flex;
            padding: 10px;
            background: #f9f9f9;
        }
        #input {
            flex: 1;
            padding: 10px;
            border: 1px solid #ccc;
            border-radius: 5px;
            font-size: 14px;
        }
        #send {
            margin-left: 10px;
            padding: 10px 20px;
            background: #007bff;
            color: white;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 14px;
        }
        #send:hover {
            background: #0056b3;
        }
        .message {
            margin: 5px 0;
            padding: 8px;
            border-radius: 5px;
            max-width: 80%;
        }
        .user-message {
            background: #e3f2fd;
            margin-left: auto;
        }
        .assistant-message {
            background: #f5f5f5;
            margin-right: auto;
        }
    </style>
</head>
<body>
    <div id="chat"></div>
    <div id="input-container">
        <input id="input" type="text" placeholder="メッセージを入力..." />
        <button id="send">送信</button>
    </div>
    <script>
        const chat = document.getElementById('chat');
        const input = document.getElementById('input');
        const send = document.getElementById('send');

        function addMessage(sender, message, isUser = false) {
            const div = document.createElement('div');
            div.className = `message ${isUser ? 'user-message' : 'assistant-message'}`;
            div.textContent = message;
            chat.appendChild(div);
            chat.scrollTop = chat.scrollHeight;
        }

        function handleSend() {
            const message = input.value.trim();
            if (message) {
                addMessage('You', message, true);
                input.value = '';

                // アシスタントの応答をシミュレート
                setTimeout(() => {
                    addMessage('Assistant', 'ご質問ありがとうございます。どのようにお手伝いできますか？');
                }, 500);
            }
        }

        send.addEventListener('click', handleSend);
        input.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                handleSend();
            }
        });
    </script>
</body>
</html>
"""

class DesktopAssistant:
    def __init__(self):
        self.window = None
        self.event_queue = Queue()

    def create_icon(self):
        """システムトレイアイコンの作成"""
        image = Image.new("RGB", (64, 64), (255, 255, 255))
        draw = ImageDraw.Draw(image)
        draw.ellipse((16, 16, 48, 48), fill="#007bff")
        return image

    def setup_tray_icon(self):
        """システムトレイアイコンのセットアップ"""
        def on_open(icon, item):
            self.event_queue.put("open_chat")

        def on_quit(icon, item):
            self.event_queue.put("quit")
            icon.stop()

        menu = Menu(
            MenuItem("チャットを開く", on_open),
            MenuItem("終了", on_quit)
        )
        icon = Icon("DesktopAssistant", self.create_icon(), "デスクトップアシスタント", menu)
        icon.run()

    def manage_webview(self):
        """WebViewの管理"""
        while True:
            event = self.event_queue.get()
            if event == "open_chat":
                if self.window is None:
                    self.window = webview.create_window(
                        'デスクトップアシスタント',
                        html=HTML_TEMPLATE,
                        width=400,
                        height=600
                    )
                    webview.start()
                    self.window = None
            elif event == "quit":
                break

    def run(self):
        """アプリケーションの実行"""
        tray_thread = threading.Thread(
            target=self.setup_tray_icon,
            args=(),
            daemon=True
        )
        tray_thread.start()
        self.manage_webview()

if __name__ == "__main__":
    app = DesktopAssistant()
    app.run()
