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
        self.is_test_mode = os.getenv("TEST_MODE", "false").lower() == "true"

    def create_icon(self):
        """システムトレイアイコンの作成"""
        image = Image.new("RGB", (64, 64), (255, 255, 255))
        draw = ImageDraw.Draw(image)
        draw.ellipse((16, 16, 48, 48), fill="#007bff")
        return image

    def setup_tray_icon(self):
        """システムトレイアイコンのセットアップ"""
        if self.is_test_mode:
            return
            
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
        if self.is_test_mode:
            return
            
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

    def run_test_mode(self):
        """テストモードでの実行"""
        from .voice_handler import VoiceHandler
        print("デスクトップアシスタント - テストモード")
        print("音声認識を開始します...")
        print("'パスタ'と言うと音声ストリーミングが開始されます")
        print("2秒間の静寂で音声ストリーミングが終了します")
        print("終了するには Ctrl+C を押してください")

        # 音声認識ハンドラーの初期化（シミュレーションモード）
        model_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "vosk-model-small-ja-0.22")
        print(f"モデルパス: {model_path}")
        voice_handler = VoiceHandler(model_path, self.event_queue, simulation_mode=True)
        voice_thread = voice_handler.start_background()

        try:
            while True:
                event = self.event_queue.get()
                if isinstance(event, tuple):
                    event_type, data = event
                    if event_type == "status":
                        print(f"ステータス: {data}")
                    elif event_type == "transcription":
                        print(f"認識テキスト: {data}")
                    elif event_type == "response":
                        print(f"サーバー応答: {data}")
                    elif event_type == "error":
                        print(f"エラー: {data}")
                elif event == "quit":
                    break
        except KeyboardInterrupt:
            print("\n終了します...")
        finally:
            voice_handler.stop()
            voice_thread.join()

    def run(self):
        """アプリケーションの実行"""
        if self.is_test_mode:
            self.run_test_mode()
        else:
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
    import os
    # テストモードで実行
    os.environ["TEST_MODE"] = "true"
    
    app = DesktopAssistant()
    try:
        app.run()
    except KeyboardInterrupt:
        print("\n終了します...")
