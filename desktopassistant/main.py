import os
import sys
import time
import threading
import importlib.util
import traceback
from queue import Queue, Empty
from typing import Optional, TYPE_CHECKING
from functools import partial

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

# HTMLテンプレートの読み込みと初期化
def get_html_template():
    """HTMLテンプレートを読み込む"""
    base_template = """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>チャットウィンドウ</title>
    <style>
        html, body {
            margin: 0;
            padding: 0;
            height: 100vh;
            background: transparent !important;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        }
        body {
            display: flex;
            flex-direction: column;
            backdrop-filter: blur(10px);
            -webkit-backdrop-filter: blur(10px);
            background-color: rgba(255, 255, 255, 0.8) !important;
        }
        #chat {
            flex: 1;
            padding: 15px;
            overflow-y: auto;
            background: transparent;
        }
        .message {
            margin: 10px 0;
            padding: 10px;
            border-radius: 8px;
            max-width: 80%;
            word-wrap: break-word;
        }
        .user-message {
            background-color: rgba(0, 123, 255, 0.1);
            margin-left: auto;
        }
        .ai-message {
            background-color: rgba(233, 236, 239, 0.8);
            margin-right: auto;
        }
        #input-container {
            display: flex;
            padding: 15px;
            background: rgba(249, 249, 249, 0.9);
            border-top: 1px solid rgba(0, 0, 0, 0.1);
        }
        #input {
            flex: 1;
            padding: 10px;
            border: 1px solid rgba(0, 0, 0, 0.2);
            border-radius: 5px;
            margin-right: 10px;
            background: rgba(255, 255, 255, 0.9);
        }
        #send {
            padding: 10px 20px;
            background: #007bff;
            color: white;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            transition: background-color 0.2s;
        }
        #send:hover {
            background: #0056b3;
        }
        /* macOS用のスタイル */
        @supports (-webkit-backdrop-filter: none) {
            body {
                -webkit-app-region: drag;
            }
            #input-container {
                -webkit-app-region: no-drag;
            }
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
            div.className = `message ${sender === 'あなた' ? 'user-message' : 'ai-message'}`;
            chat.appendChild(div);
            chat.scrollTop = chat.scrollHeight;
        }

        send.addEventListener('click', () => {
            const message = input.value.trim();
            if (message) {
                addMessage('あなた', message);
                input.value = '';

                // AIの応答をシミュレート
                setTimeout(() => {
                    const response = 'これは次のメッセージへの応答です: ' + message;
                    addMessage('AI', response);
                }, 500);
            }
        });

        input.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                send.click();
            }
        });

        // macOS用の透過設定
        if (window.pywebview && window.pywebview.platform === 'cocoa') {
            document.documentElement.style.background = 'transparent';
            document.body.style.background = 'transparent';
        }
    </script>
</body>
</html>
"""
    return base_template

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
        
    def init_macos_menu(self):
        """macOS用のメニューを初期化"""
        print("Initializing macOS menu...")
        try:
            import AppKit
            from PyObjCTools import AppHelper

            def setup_menu():
                # メインメニューの作成
                mainMenu = AppKit.NSMenu.alloc().init()
                mainMenu.setTitle_("デスクトップアシスタント")  # タイトルを先に設定
                AppKit.NSApplication.sharedApplication().setMainMenu_(mainMenu)

                # アプリケーションメニューの作成
                mainAppMenuItem = AppKit.NSMenuItem.alloc().init()
                mainMenu.insertItem_atIndex_(mainAppMenuItem, 0)
                appMenu = AppKit.NSMenu.alloc().init()
                appMenu.setTitle_("アプリケーション")
                mainAppMenuItem.setSubmenu_(appMenu)

                # メニュー項目の追加
                appMenu.addItemWithTitle_action_keyEquivalent_(
                    "終了", "terminate:", "q"
                )

            # メインスレッドでメニューをセットアップ
            if threading.current_thread() is threading.main_thread():
                setup_menu()
            else:
                AppHelper.callAfter(setup_menu)
            print("macOS menu initialized successfully")
        except Exception as e:
            print(f"Error initializing macOS menu: {e}")
            import traceback
            traceback.print_exc()

    def setup_platform(self):
        """プラットフォーム固有の設定を初期化"""
        print(f"Initializing for platform: {sys.platform}")
        
        if sys.platform == 'darwin':
            self.gui_backend = 'cocoa'
            print("Using cocoa backend for macOS")
            self.init_macos_menu()  # macOS用メニューの初期化
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
            if IS_MACOS:
                # macOSの場合はAppHelperを使用してメインスレッドで表示
                from PyObjCTools import AppHelper
                def show_window():
                    try:
                        window = webview.windows[0]
                        if window:
                            window.show()
                            print("Window show command executed on main thread")
                    except Exception as e:
                        print(f"Error showing window: {e}")
                AppHelper.callAfter(show_window)
            else:
                # 他のプラットフォームではイベントキューを使用
                self.event_queue.put("open_chat")

        def on_quit(icon, item):
            print("Menu: 終了 clicked")
            if IS_MACOS:
                # macOSの場合はメインスレッドでクリーンアップ
                from PyObjCTools import AppHelper
                def cleanup():
                    try:
                        # ウィンドウを非表示
                        window = webview.windows[0]
                        if window:
                            window.hide()
                        # 終了処理
                        self.event_queue.put("quit")
                        self.stop_event.set()
                        icon.stop()
                        print("Cleanup executed on main thread")
                    except Exception as e:
                        print(f"Error during cleanup: {e}")
                AppHelper.callAfter(cleanup)
            else:
                self.event_queue.put("quit")
                self.stop_event.set()
                icon.stop()

        # メニューの作成（プラットフォームに応じて）
        if IS_MACOS:
            # macOSの場合は最小限のメニュー（メインメニューは別途作成済み）
            menu = Menu(MenuItem("チャットを開く", on_open))
        else:
            # 他のプラットフォームでは通常のメニュー
            menu = Menu(
                MenuItem("チャットを開く", on_open),
                MenuItem("終了", on_quit)
            )
        
        # プラットフォームに応じたアイコン設定
        title = "デスクトップアシスタント"
        self.tray_icon = Icon("DesktopAssistant", self.create_icon(), title, menu)
        
        # macOSの場合はメインスレッドでアイコンを初期化
        if IS_MACOS:
            from PyObjCTools import AppHelper
            AppHelper.callAfter(self.tray_icon.run)
            
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
            
            # macOSの場合はメインメニューを先に初期化
            if IS_MACOS and threading.current_thread() is threading.main_thread():
                self.init_macos_menu()
            
            # WebViewの初期化
            try:
                print("Creating WebView window...")
                # ウィンドウの作成とプラットフォーム固有の設定
                window_options = {
                    'title': 'デスクトップアシスタント',
                    'html': HTML_TEMPLATE,
                    'width': 400,
                    'height': 600,
                    'on_top': True,
                    'hidden': True,  # 初期状態では非表示
                    'easy_drag': True,  # ドラッグ可能に
                    'text_select': True,  # テキスト選択を許可
                }

                if IS_MACOS:
                    # macOS固有の設定
                    window_options.update({
                        'frameless': True,
                        'transparent': True,
                        'background_color': '#00000000',  # 完全な透明
                        'vibrancy': True,  # macOSのビブランシー効果を有効化
                    })
                    
                    # カスタムJavaScriptを注入してWebViewの背景を透明に
                    window_options['js_api'] = {
                        'setTransparent': '''
                            document.body.style.background = 'transparent';
                            document.documentElement.style.background = 'transparent';
                        ''',
                        'initMacOS': '''
                            // macOS用の初期化
                            if (window.pywebview && window.pywebview.platform === 'cocoa') {
                                // ウィンドウの透明度を設定
                                document.documentElement.style.background = 'transparent';
                                document.body.style.background = 'transparent';
                                
                                // ドラッグ可能な領域を設定
                                document.body.style.webkitAppRegion = 'drag';
                                document.querySelector('#input-container').style.webkitAppRegion = 'no-drag';
                                
                                // 透明度とアニメーションを設定
                                document.body.style.transition = 'background-color 0.3s';
                                document.body.style.backgroundColor = 'rgba(255, 255, 255, 0.85)';
                            }
                        '''
                    }

                print("Creating window with options:", window_options)
                self.window = webview.create_window(**window_options)
                
                if IS_MACOS:
                    # macOS用の追加設定
                    import AppKit
                    from PyObjCTools import AppHelper
                    
                    def configure_window_transparency(window):
                        """ウィンドウの透明度を設定"""
                        try:
                            if not window or not hasattr(window, 'native'):
                                print("Window not ready for transparency configuration")
                                return
                            
                            native_window = window.native
                            if not native_window:
                                print("Native window not available")
                                return
                                
                            print("Configuring native window transparency...")
                            native_window.setOpaque_(False)
                            native_window.setHasShadow_(True)  # シャドウは表示
                            native_window.setBackgroundColor_(
                                AppKit.NSColor.clearColor()
                            )
                            
                            # モダンなビブランシー効果を設定
                            if hasattr(native_window, 'visualEffectView'):
                                native_window.visualEffectView().setBlendingMode_(
                                    AppKit.NSVisualEffectBlendingModeBehindWindow
                                )
                            print("Window transparency configured successfully")
                        except Exception as e:
                            print(f"Error configuring window transparency: {e}")
                            import traceback
                            traceback.print_exc()
                    
                    # ウィンドウ作成後に透明度を設定
                    def setup_window():
                        """ウィンドウのセットアップ（メインスレッド）"""
                        if self.window:
                            configure_window_transparency(self.window)
                        else:
                            print("Window not available for setup")
                    
                    # メインスレッドで実行（遅延付き）
                    def delayed_setup():
                        """遅延付きのウィンドウセットアップ"""
                        time.sleep(0.1)  # ウィンドウの初期化を待つ
                        setup_window()
                    
                    if threading.current_thread() is threading.main_thread():
                        delayed_setup()
                    else:
                        AppHelper.callAfter(delayed_setup)
                print("Window created successfully")
                print(f"Initial window state: visible={getattr(self.window, 'visible', None)}")
                print(f"Window properties: frameless={getattr(self.window, 'frameless', None)}, "
                      f"transparent={getattr(self.window, 'transparent', None)}")

                # システムトレイとWebViewをメインスレッドで実行
                print(f"Starting application with {self.gui_backend} backend...")
                
                # システムトレイを初期化（メインスレッドで実行）
                if IS_MACOS:
                    from PyObjCTools import AppHelper
                    tray_icon = self.setup_tray_icon()
                    AppHelper.callAfter(tray_icon.run)
                else:
                    # 他のプラットフォームでは従来通り別スレッドで実行
                    tray_icon = self.setup_tray_icon()
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
            # クリーンアップ処理
            if IS_MACOS:
                # メインメニューのクリーンアップ
                try:
                    import AppKit
                    mainMenu = AppKit.NSApplication.sharedApplication().mainMenu()
                    if mainMenu:
                        mainMenu.removeAllItems()
                except Exception as e:
                    print(f"Error cleaning up main menu: {e}")
            self.cleanup()

if __name__ == "__main__":
    app = DesktopAssistant()
    app.run()
