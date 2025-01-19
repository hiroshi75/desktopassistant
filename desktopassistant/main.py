import os
import sys
import time
import threading
import importlib.util
import traceback
from queue import Queue, Empty
from typing import Optional, TYPE_CHECKING

import webview
from PIL import Image, ImageDraw

if TYPE_CHECKING:
    from .voice_handler import VoiceHandler

# macOSではウェイクワード機能を無効化
ENABLE_VOICE_HANDLER = sys.platform != 'darwin'

# プラットフォーム固有の設定
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
        self.voice_handler: Optional['VoiceHandler'] = None
        self.window_ready = threading.Event()
        
        # プラットフォーム固有の初期化
        self.setup_platform()
        
    def setup_platform(self):
        """プラットフォーム固有の設定を初期化"""
        print(f"Initializing for platform: {sys.platform}")
        
        if sys.platform == 'darwin':
            self.gui_backend = 'cocoa'
            print("Using cocoa backend for macOS")
        elif sys.platform == 'linux':
            # Linux環境の場合はQtを使用
            try:
                # X11の設定を確認
                if not os.environ.get('DISPLAY'):
                    print("DISPLAY not set, attempting to set default...")
                    os.environ['DISPLAY'] = ':0'
                
                # QtのPythonバインディングを確認
                qt_available = importlib.util.find_spec('PyQt5') is not None
                if not qt_available:
                    print("Warning: PyQt5 not found. Please install: pip install PyQt5")
                
                self.gui_backend = 'qt'
                print("Using Qt backend for Linux")
            except Exception as e:
                print(f"Warning: Error setting up Linux environment: {e}")
                print("Falling back to gtk backend...")
                self.gui_backend = 'gtk'
        else:
            self.gui_backend = 'qt'
            print(f"Using Qt backend for platform: {sys.platform}")
        
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
            print("Menu: チャットを開く clicked")
            # メインスレッドでウィンドウを直接表示
            if sys.platform == 'darwin':
                # macOSの場合は直接表示
                webview.windows[0].show()
            else:
                # 他のプラットフォームではイベントキューを使用
                self.event_queue.put("open_chat")

        def on_quit(icon, item):
            print("Menu: 終了 clicked")
            self.event_queue.put("quit")
            self.stop_event.set()
            print("Stopping system tray icon...")
            icon.stop()
            print("System tray icon stopped")

        menu = Menu(
            MenuItem("チャットを開く", on_open),
            MenuItem("終了", on_quit)
        )
        
        # プラットフォームに応じたアイコン設定
        title = "デスクトップアシスタント"
        self.tray_icon = Icon("DesktopAssistant", self.create_icon(), title, menu)
        return self.tray_icon

    def window_manager(self, target_window):
        """ウィンドウの表示状態を管理する関数"""
        print("Window manager started")
        print(f"Starting event loop with {self.gui_backend} backend")
        
        def handle_event(event):
            """イベントを処理し、UIの更新をメインスレッドで実行"""
            print(f"Processing event: {event}")
            try:
                # 常にメインウィンドウを使用
                window = webview.windows[0] if IS_MACOS else target_window
                
                if event == "open_chat":
                    print("Showing window...")
                    print(f"Current window state: visible={getattr(window, 'visible', None)}")
                    try:
                        window.show()
                        print("Window show command executed successfully")
                    except Exception as e:
                        print(f"Error showing window: {e}")
                        traceback.print_exc()
                    print(f"New window state: visible={getattr(window, 'visible', None)}")
                elif event == "quit":
                    print("Hiding window and cleaning up...")
                    print(f"Current window state: visible={getattr(window, 'visible', None)}")
                    try:
                        window.hide()
                        print("Window hide command executed successfully")
                        # ウィンドウが非表示になるのを待つ
                        if IS_MACOS:
                            time.sleep(0.1)
                    except Exception as e:
                        print(f"Error hiding window: {e}")
                        traceback.print_exc()
                    print(f"New window state: visible={getattr(window, 'visible', None)}")
                    print("Window hide command executed")
                    self.stop_event.set()
                    return True  # 終了を示す
                return False  # 継続を示す
            except Exception as e:
                print(f"Error handling event {event}: {e}")
                traceback.print_exc()
                return False
        
        # メインループ
        while not self.stop_event.is_set():
            try:
                # イベントの取得（タイムアウト付き）
                event = self.event_queue.get(timeout=0.1)
                if handle_event(event):
                    print("Quit event processed, breaking event loop")
                    break
            except Empty:
                continue  # タイムアウト時は継続
            except Exception as e:
                print(f"Error in window management: {e}")
                traceback.print_exc()
                if self.stop_event.is_set():
                    break
        
        print("Window manager stopped")

    def cleanup(self):
        """アプリケーションのクリーンアップ処理"""
        print("Starting cleanup...")
        
        # 音声ハンドラーの停止
        if self.voice_handler:
            print("Stopping voice handler...")
            try:
                self.voice_handler.stop()
                print("Voice handler stopped")
            except Exception as e:
                print(f"Error stopping voice handler: {e}")
        
        # 停止イベントの設定
        print("Setting stop event...")
        self.stop_event.set()
        print("Stop event set")

        # ウィンドウの非表示化（メインスレッドで実行）
        if hasattr(self, 'window') and self.window:
            print("Hiding window...")
            try:
                if sys.platform == 'darwin':
                    # macOSの場合は直接ウィンドウを非表示
                    webview.windows[0].hide()
                else:
                    self.window.hide()
                print("Window hidden")
            except Exception as e:
                print(f"Error hiding window: {e}")

        # イベントキューをクリア
        print("Clearing event queue...")
        try:
            while True:
                self.event_queue.get_nowait()
        except Empty:
            pass
        print("Event queue cleared")

        # システムトレイアイコンの停止
        if hasattr(self, 'tray_icon'):
            print("Stopping system tray icon...")
            try:
                self.tray_icon.stop()
                print("System tray icon stopped")
            except Exception as e:
                print(f"Error stopping tray icon: {e}")

        print("Cleanup completed")
        
        # プロセスの終了を確実に
        try:
            if threading.current_thread() is threading.main_thread():
                sys.exit(0)
            else:
                # メインスレッド以外からの終了時は、メインスレッドに終了を通知
                print("Cleanup called from non-main thread, requesting main thread exit...")
                self.event_queue.put("quit")
        except Exception as e:
            print(f"Error during exit: {e}")
            traceback.print_exc()
            os._exit(1)  # 強制終了

    def run(self):
        """アプリケーションの実行"""
        try:
            print("Initializing application on main thread...")
            
            # WebViewの初期化
            try:
                print("Creating WebView window...")
                self.window = webview.create_window(
                    'デスクトップアシスタント',
                    html=HTML_TEMPLATE,
                    width=400,
                    height=600,
                    on_top=True,
                    hidden=True,  # 初期状態では非表示
                    frameless=IS_MACOS,  # macOSではフレームレスウィンドウを使用
                    easy_drag=True,  # ドラッグ可能に
                    text_select=True,  # テキスト選択を許可
                    transparent=IS_MACOS,  # macOSでは透過を有効に
                )
                print("Window created successfully")
                print(f"Initial window state: visible={getattr(self.window, 'visible', None)}")
                print(f"Window properties: frameless={getattr(self.window, 'frameless', None)}, "
                      f"transparent={getattr(self.window, 'transparent', None)}")

                # システムトレイとWebViewをメインスレッドで実行
                print(f"Starting application with {self.gui_backend} backend...")
                
                # システムトレイを初期化（非同期）
                tray_icon = self.setup_tray_icon()
                import threading
                tray_thread = threading.Thread(
                    target=lambda: tray_icon.run(),
                    daemon=True
                )
                tray_thread.start()
                
                # WebViewを開始（メインスレッドで実行）
                print(f"Starting WebView with {self.gui_backend} backend...")
                webview.start(
                    func=self.window_manager,
                    args=(self.window,),
                    gui=self.gui_backend
                )
            except Exception as e:
                print(f"Error initializing application: {e}")
                import traceback
                traceback.print_exc()
                return
        finally:
            self.cleanup()

if __name__ == "__main__":
    app = DesktopAssistant()
    app.run()
