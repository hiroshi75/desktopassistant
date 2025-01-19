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
    """システムトレイアイコンの作成
    
    macOSメニューバー用に透過背景とRetinaディスプレイ用の高解像度に対応
    """
    # macOSのメニューバーアイコン用に2倍の解像度で作成
    image = Image.new("RGBA", (128, 128), (0, 0, 0, 0))  # 透明背景
    draw = ImageDraw.Draw(image)
    
    # 円を描画（中心に配置）
    margin = 32  # 余白
    size = 128 - (margin * 2)  # 円のサイズ
    draw.ellipse((margin, margin, margin + size, margin + size), 
                fill="#007bff")
    
    # 表示サイズにリサイズ（アンチエイリアス有効）
    return image.resize((64, 64), Image.Resampling.LANCZOS)


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

    # メインスレッドでWebViewを管理（UIの要件）
    manage_webview(event_queue)
