import threading
from queue import Queue

import webview
from PIL import Image, ImageDraw
from pystray import Icon, Menu, MenuItem

# HTMLのテンプレート
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>チャットウィンドウ</title>
    <style>
        body {
            font-family: Arial, sans-serif;
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
        }
        #send {
            margin-left: 10px;
            padding: 10px 20px;
            background: #007bff;
            color: white;
            border: none;
            border-radius: 5px;
            cursor: pointer;
        }
        #send:hover {
            background: #0056b3;
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

        function addMessage(sender, message) {
            const div = document.createElement('div');
            div.textContent = `${sender}: ${message}`;
            chat.appendChild(div);
            chat.scrollTop = chat.scrollHeight;
        }

        send.addEventListener('click', () => {
            const message = input.value.trim();
            if (message) {
                addMessage('あなた', message);
                input.value = '';

                // AIの応答をシミュレート
                setTimeout(
                    () => {
                        const response = 'これは次のメッセージへの応答です: ' + message;
                        addMessage('AI', response);
                    },
                    500
                );
            }
        });
    </script>
</body>
</html>
"""


# システムトレイアイコン用の画像を作成
def create_icon():
    image = Image.new("RGB", (64, 64), (255, 255, 255))
    draw = ImageDraw.Draw(image)
    draw.ellipse((16, 16, 48, 48), fill="blue")
    return image


# システムトレイのセットアップ
def setup_tray_icon(queue):
    def on_open(icon, item):
        queue.put("open_chat")  # メインスレッドに通知

    def on_quit(icon, item):
        queue.put("quit")  # メインスレッドに通知
        icon.stop()

    menu = Menu(MenuItem("チャットを開く", on_open), MenuItem("終了", on_quit))
    icon = Icon("ChatApp", create_icon(), "チャットアプリ", menu)
    icon.run()


# メインスレッドでWebViewを管理
def manage_webview(queue):
    window = None
    while True:
        event = queue.get()
        if event == "open_chat":
            if window is None:  # ウィンドウが開かれていない場合のみ作成
                window = webview.create_window(
                    "チャットウィンドウ", html=HTML_TEMPLATE, width=400, height=500
                )
                webview.start()  # ブロッキング呼び出し
                window = None  # ウィンドウを閉じた後はリセット
        elif event == "quit":
            break


# メイン関数
if __name__ == "__main__":
    event_queue = Queue()

    # システムトレイを別スレッドで実行
    tray_thread = threading.Thread(
        target=setup_tray_icon, args=(event_queue,), daemon=True
    )
    tray_thread.start()

    # メインスレッドでWebViewを管理
    manage_webview(event_queue)
