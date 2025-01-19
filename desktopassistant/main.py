import webview
import threading
import sys
import traceback
from PIL import Image, ImageDraw
from queue import Queue
import os

# プラットフォーム判定
IS_MACOS = sys.platform == 'darwin'

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
        self._rumps_app = None
        self.setup_platform()
        
    def setup_platform(self):
        """プラットフォーム固有の初期化を行う"""
        if IS_MACOS:
            try:
                from .macos_rumps_app import MacOSMenuBarApp
                self._rumps_app = MacOSMenuBarApp()
                if self._rumps_app is not None:
                    self._rumps_app.event_queue = self.event_queue
                    print("macOS menu bar app initialized successfully")
                else:
                    print("Warning: Failed to initialize macOS menu bar app")
            except Exception as e:
                print(f"Error initializing macOS menu bar app: {e}")
                traceback.print_exc()
                self._rumps_app = None

    def create_icon(self):
        """システムトレイアイコンの作成"""
        image = Image.new("RGB", (64, 64), (255, 255, 255))
        draw = ImageDraw.Draw(image)
        draw.ellipse((16, 16, 48, 48), fill="#007bff")
        return image

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
        if IS_MACOS:
            # macOSの場合はrumpsアプリを実行
            if self._rumps_app is not None:
                try:
                    if threading.current_thread() is threading.main_thread():
                        self._rumps_app.run()
                    else:
                        from PyObjCTools import AppHelper
                        AppHelper.callAfter(self._rumps_app.run)
                except Exception as e:
                    print(f"Error running macOS menu bar app: {e}")
                    traceback.print_exc()
                    # フォールバック: pystrayを使用
                    print("Falling back to pystray implementation")
                    self._fallback_to_pystray()
            else:
                print("macOS menu bar app not initialized, falling back to pystray")
                self._fallback_to_pystray()
        else:
            self._fallback_to_pystray()
            
    def _fallback_to_pystray(self):
        """pystrayを使用したフォールバック実装"""
        # システムトレイアイコンのスレッド開始
        tray_thread = threading.Thread(
            target=self.setup_tray_icon,
            args=(),
            daemon=True
        )
        tray_thread.start()

        # WebViewの管理（メインループ）
        self.manage_webview()

if __name__ == "__main__":
    app = DesktopAssistant()
    app.run()
