import unittest
import sys
import os
import threading
from unittest.mock import patch, MagicMock, call

# メインアプリケーションのパスを追加
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

# モジュールレベルでモックを作成
mock_webview = MagicMock()
mock_app_helper = MagicMock()
mock_rumps = MagicMock()
mock_main = MagicMock()

# HTMLテンプレートのモック
mock_html_template = """
<!DOCTYPE html>
<html><body><h1>Test Template</h1></body></html>
"""
mock_main.HTML_TEMPLATE = mock_html_template

# モジュールをモック化
sys.modules['pywebview'] = mock_webview
sys.modules['rumps'] = mock_rumps
sys.modules['desktopassistant.main'] = mock_main

# PyObjCToolsのモック化
mock_app_helper = MagicMock()
mock_app_helper.callAfter = MagicMock(side_effect=lambda func, *args, **kwargs: func(*args, **kwargs))
sys.modules['PyObjCTools.AppHelper'] = mock_app_helper

# rumpsの基本的な機能をモック化
class MockMenuItem:
    def __init__(self, title, callback=None):
        self.title = title
        self._callback = callback
        
    def __str__(self):
        return self.title

mock_rumps.MenuItem = MockMenuItem
mock_rumps.App = MagicMock

# プラットフォーム判定を強制的にmacOSに設定
sys.platform = 'darwin'
IS_MACOS = True

class TestSystemTray(unittest.TestCase):
    def test_macos_window_operations(self):
        """macOSウィンドウ操作のテスト"""
        # モックウィンドウの設定
        mock_window = MagicMock()
        mock_webview.windows = []
        mock_webview.create_window.return_value = mock_window
        
        # モジュールのインポート前にモックを設定
        with patch('desktopassistant.macos_rumps_app.HTML_TEMPLATE', mock_html_template):
            from desktopassistant.macos_rumps_app import MacOSMenuBarApp
            app = MacOSMenuBarApp()
            
            # チャットを開く操作のテスト
            with patch('threading.current_thread', return_value=threading.main_thread()):
                app.open_chat(None)
            
            # ウィンドウが作成され、表示されることを確認
            mock_webview.create_window.assert_called_once_with(
                title="デスクトップアシスタント",
                html=mock_html_template,
                width=400,
                height=600,
                resizable=True,
                frameless=True,
                easy_drag=True,
                background_color="#00000000",
                transparent=True,
                on_top=True
            )
            self.assertTrue(mock_window.show.called)
            self.assertIsNotNone(app._window)
            
            # 終了操作のテスト
            app.quit_app(None)
            self.assertTrue(mock_window.hide.called)
            self.assertIsNone(app._window)
    
    def test_window_thread_safety(self):
        """ウィンドウ操作のスレッドセーフティテスト"""
        # モックウィンドウの設定
        mock_window = MagicMock()
        mock_webview.windows = []
        mock_webview.create_window.return_value = mock_window
        
        from desktopassistant.macos_rumps_app import MacOSMenuBarApp
        app = MacOSMenuBarApp()
        
        # メインスレッドでの実行テスト
        with patch('threading.current_thread', return_value=threading.main_thread()):
            app._ensure_window_exists()
            mock_webview.create_window.assert_called_once()
            self.assertFalse(mock_app_helper.callAfter.called)
        
        # 非メインスレッドでの実行テスト
        with patch('threading.current_thread', return_value=MagicMock()):
            mock_webview.create_window.reset_mock()
            app._window = None
            app._ensure_window_exists()
            self.assertTrue(mock_app_helper.callAfter.called)

if __name__ == '__main__':
    unittest.main()
