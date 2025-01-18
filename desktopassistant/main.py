import webview
import threading
from PIL import Image, ImageDraw
from queue import Queue
import os
import platform
from desktopassistant.voice_handler import VoiceHandler

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
        self.voice_handler = VoiceHandler(
            model_path="vosk-model-small-ja-0.22/vosk-model-small-ja-0.22",
            event_queue=self.event_queue
        )

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
                        height=600
                    )
                    webview.start()
                    self.window = None
                else:
                    # Windowsの場合のみウィンドウを前面に表示
                    if platform.system() == 'Windows':
                        try:
                            import win32gui
                            import win32con
                            hwnd = win32gui.FindWindow(None, 'デスクトップアシスタント')
                            if hwnd:
                                win32gui.SetForegroundWindow(hwnd)
                                win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
                        except ImportError:
                            print("pywin32がインストールされていません。最前面表示はスキップします。")
            elif event == "quit":
                break

    def run(self):
        """アプリケーションの実行"""
        # システムトレイアイコンのスレッド開始
        tray_thread = threading.Thread(
            target=self.setup_tray_icon,
            args=(),
            daemon=True
        )
        tray_thread.start()

        # 音声認識のスレッド開始
        voice_thread = self.voice_handler.start_background()

        # WebViewの管理（メインループ）
        self.manage_webview()

        # 終了時のクリーンアップ
        self.voice_handler.stop()
        voice_thread.join(timeout=1.0)  # 最大1秒待機

if __name__ == "__main__":
    app = DesktopAssistant()
    app.run()
