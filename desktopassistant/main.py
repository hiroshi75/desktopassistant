import webview
import threading
from PIL import Image, ImageDraw
from queue import Queue
import os

# Lazy import of pystray to improve testability
def get_pystray():
    from pystray import Icon, Menu, MenuItem
    return Icon, Menu, MenuItem

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
        self.stop_event = threading.Event()

    def create_icon(self):
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

    def setup_tray_icon(self):
        """システムトレイアイコンのセットアップ"""
        Icon, Menu, MenuItem = get_pystray()
        
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
                        height=600,
                        on_top=True
                    )
                    webview.start(gui='qt')
                    self.window = None
            elif event == "quit":
                break

    def run(self):
        """アプリケーションの実行"""
        # システムトレイアイコンを別スレッドで実行
        tray_thread = threading.Thread(
            target=self.setup_tray_icon,
            args=(),
            daemon=True
        )
        tray_thread.start()

        # メインスレッドでWebViewを管理（UIの要件）
        self.manage_webview()

if __name__ == "__main__":
    app = DesktopAssistant()
    app.run()
