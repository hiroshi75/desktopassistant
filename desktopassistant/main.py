import webview
import threading
import sys
import traceback
from PIL import Image, ImageDraw
from queue import Queue
import os

# プラットフォーム判定
IS_MACOS = sys.platform == 'darwin'

# Lazy import of pystray for non-macOS platforms
def get_pystray():
    """非macOSプラットフォーム用のpystrayをインポート
    
    Returns:
        tuple: (Icon, Menu, MenuItem) if not on macOS, or None if import fails
    """
    try:
        if not IS_MACOS:
            from pystray import Icon, Menu, MenuItem
            return Icon, Menu, MenuItem
    except ImportError:
        print("Warning: pystray import failed")
    return None

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
            from .macos_rumps_app import MacOSMenuBarApp
            self._rumps_app = MacOSMenuBarApp()

    def create_icon(self):
        """システムトレイアイコンの作成"""
        image = Image.new("RGB", (64, 64), (255, 255, 255))
        draw = ImageDraw.Draw(image)
        draw.ellipse((16, 16, 48, 48), fill="#007bff")
        return image

    def setup_tray_icon(self):
        """非macOSプラットフォーム用のシステムトレイアイコンのセットアップ"""
        if IS_MACOS:
            return
            
        pystray_components = get_pystray()
        if not pystray_components:
            print("Warning: pystray not available")
            return
            
        Icon, Menu, MenuItem = pystray_components
            
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
                    raise
        else:
            # 非macOSの場合はpystrayを使用
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
