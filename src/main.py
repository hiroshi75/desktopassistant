import webview
import threading
from pystray import Icon, Menu, MenuItem
from PIL import Image, ImageDraw
from queue import Queue
import os

# HTMLテンプレートの読み込み
def get_html_template():
    """HTMLテンプレートを読み込む"""
    template_path = os.path.join(os.path.dirname(__file__), 'templates', 'chat.html')
    with open(template_path, 'r', encoding='utf-8') as f:
        return f.read()

HTML_TEMPLATE = get_html_template()

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
