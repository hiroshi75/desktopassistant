import webview
import threading
from PIL import Image, ImageDraw
from queue import Queue, Empty
import os
import sys
from typing import Optional

# macOSではウェイクワード機能を無効化
ENABLE_VOICE_HANDLER = sys.platform != 'darwin'

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
        self.voice_handler: Optional['VoiceHandler'] = None
        self.window_ready = threading.Event()
        self.gui_backend = 'cocoa' if sys.platform == 'darwin' else 'qt'
        
        # macOS以外の場合のみVoiceHandlerを初期化
        if ENABLE_VOICE_HANDLER:
            try:
                from .voice_handler import VoiceHandler
                self.voice_handler = VoiceHandler("path/to/model", self.event_queue)
                self.voice_handler.start_background()
            except ImportError:
                print("Warning: Voice recognition features are not available")

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
        def window_manager(window):
            """ウィンドウの表示状態を管理する関数"""
            print("Window manager started")
            while not self.stop_event.is_set():
                try:
                    event = self.event_queue.get(timeout=0.1)  # タイムアウトを設定してCPU使用率を抑える
                    print(f"Received event: {event}")
                    
                    if event == "open_chat":
                        print("Showing window...")
                        window.show()
                    elif event == "quit":
                        print("Hiding window...")
                        window.hide()
                        self.stop_event.set()
                        break
                except Empty:
                    continue
                except Exception as e:
                    print(f"Error in window management: {e}")
            print("Window manager stopped")

        # WebViewの開始（window_managerを渡して状態管理を行う）
        print(f"Starting WebView with {self.gui_backend} backend...")
        webview.start(window_manager, self.window, gui=self.gui_backend)

    def run(self):
        """アプリケーションの実行"""
        try:
            # WebViewの初期化（メインスレッドで実行）
            try:
                print("Creating WebView window...")
                self.window = webview.create_window(
                    'デスクトップアシスタント',
                    html=HTML_TEMPLATE,
                    width=400,
                    height=600,
                    on_top=True,
                    hidden=True  # 初期状態では非表示
                )
                print("Window created successfully")
                print(f"Initial window state: visible={getattr(self.window, 'visible', None)}")
            except Exception as e:
                print(f"Error initializing WebView: {e}")
                return

            # システムトレイとWebViewをメインスレッドで実行
            self.setup_tray_icon()
            # メインスレッドでWebViewを管理
            self.manage_webview()
        finally:
            # 終了時のクリーンアップ
            if self.voice_handler:
                self.voice_handler.stop()
            self.stop_event.set()

if __name__ == "__main__":
    app = DesktopAssistant()
    app.run()
