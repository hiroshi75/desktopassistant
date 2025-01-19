"""macOS用のネイティブメニューバー実装

このモジュールは、rumpsを使用してmacOS用のネイティブメニューバーを実装します。
webviewベースのチャットインターフェースと統合されています。
"""
import os
import sys
import threading
from typing import Optional

import rumps
import pywebview as webview

from desktopassistant.main import HTML_TEMPLATE

class MacOSMenuBarApp(rumps.App):
    """macOS用のメニューバーアプリケーション
    
    rumps.Appを継承し、ネイティブなmacOSメニューバーを提供します。
    webviewベースのチャットウィンドウと統合されています。
    """
    
    def __init__(self, name: str = "デスクトップアシスタント"):
        """メニューバーアプリケーションの初期化
        
        Args:
            name: アプリケーション名（デフォルト: "デスクトップアシスタント"）
        """
        # アプリケーションアイコンのパスを取得
        icon_path = os.path.join(os.path.dirname(__file__), "assets", "icon.png")
        if not os.path.exists(icon_path):
            icon_path = None  # アイコンが見つからない場合はデフォルトを使用
            
        super().__init__(name=name, icon=icon_path, quit_button=None)
        
        # メニュー項目の設定
        self.menu = [
            rumps.MenuItem("チャットを開く"),
            None,  # セパレータ
            rumps.MenuItem("終了")
        ]
        
        # チャットウィンドウの状態管理
        self._window: Optional[webview.Window] = None
        
    def _ensure_window_exists(self) -> None:
        """チャットウィンドウが存在することを確認
        
        存在しない場合は新しいウィンドウを作成します。
        すべてのウィンドウ操作はメインスレッドで実行されます。
        """
        from PyObjCTools import AppHelper
        
        def create_window():
            if not self._window:
                if webview.windows:
                    self._window = webview.windows[0]
                else:
                    self._window = webview.create_window(
                        title="デスクトップアシスタント",
                        html=HTML_TEMPLATE,
                        width=400,
                        height=600,
                        resizable=True,
                        frameless=True,
                        easy_drag=True,
                        background_color="#00000000",
                        transparent=True,
                        on_top=True
                    )
        
        if threading.current_thread() is threading.main_thread():
            create_window()
        else:
            AppHelper.callAfter(create_window)
    
    @rumps.clicked("チャットを開く")
    def open_chat(self, _) -> None:
        """チャットウィンドウを開く
        
        既存のウィンドウがある場合はそれを表示し、
        ない場合は新しいウィンドウを作成します。
        """
        try:
            self._ensure_window_exists()
            if self._window:
                from PyObjCTools import AppHelper
                AppHelper.callAfter(self._window.show)
        except Exception as e:
            print(f"Error in open_chat: {e}")
            rumps.notification(
                title="エラー",
                subtitle="チャットウィンドウを開けませんでした",
                message=str(e)
            )
    
    @rumps.clicked("終了")
    def quit_app(self, _) -> None:
        """アプリケーションを終了
        
        チャットウィンドウを閉じ、アプリケーションを終了します。
        """
        try:
            # チャットウィンドウが存在する場合は閉じる
            if self._window:
                from PyObjCTools import AppHelper
                AppHelper.callAfter(self._window.hide)
                self._window = None
            
            # アプリケーションを終了
            rumps.quit_application()
        except Exception as e:
            print(f"Error in quit_app: {e}")
            rumps.notification(
                title="エラー",
                subtitle="アプリケーションの終了中にエラーが発生しました",
                message=str(e)
            )
    
    def run(self, debug: bool = False) -> None:
        """アプリケーションを実行
        
        Args:
            debug: デバッグモードで実行するかどうか（デフォルト: False）
        """
        if debug:
            rumps.debug_mode(True)
        super().run()
