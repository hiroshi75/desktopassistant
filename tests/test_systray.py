import unittest
import sys
import os
import threading
from unittest.mock import patch, MagicMock, call

# メインアプリケーションのパスを追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# プラットフォーム判定
IS_MACOS = sys.platform == 'darwin'

class TestSystemTray(unittest.TestCase):
    @patch('desktopassistant.macos_rumps_app.webview')
    @patch('desktopassistant.macos_rumps_app.AppHelper')
    def test_macos_window_operations(self, mock_app_helper, mock_webview):
        """macOSウィンドウ操作のテスト"""
        # モックウィンドウの設定
        mock_window = MagicMock()
        mock_webview.windows = []
        mock_webview.create_window.return_value = mock_window
        
        # Import here to avoid early initialization
        from desktopassistant.macos_rumps_app import MacOSMenuBarApp
        
        # アプリケーションの初期化
        app = MacOSMenuBarApp()
        
        # チャットを開く操作のテスト
        app.open_chat(None)
        mock_webview.create_window.assert_called_once()
        mock_app_helper.callAfter.assert_called_with(mock_window.show)
        
        # 終了操作のテスト
        app.quit_app(None)
        self.assertIsNone(app._window)
        
    @patch('desktopassistant.macos_rumps_app.webview')
    @patch('threading.current_thread')
    def test_window_thread_safety(self, mock_current_thread, mock_webview):
        """ウィンドウ操作のスレッドセーフティテスト"""
        # モックの設定
        mock_window = MagicMock()
        mock_webview.windows = []
        mock_webview.create_window.return_value = mock_window
        
        from desktopassistant.macos_rumps_app import MacOSMenuBarApp
        app = MacOSMenuBarApp()
        
        # メインスレッドでの実行テスト
        mock_current_thread.return_value = threading.main_thread()
        app._ensure_window_exists()
        mock_webview.create_window.assert_called_once()
        
        # 非メインスレッドでの実行テスト
        mock_current_thread.return_value = MagicMock()  # 非メインスレッド
        mock_webview.create_window.reset_mock()
        app._window = None
        app._ensure_window_exists()
        from desktopassistant.macos_rumps_app import AppHelper
        self.assertTrue(AppHelper.callAfter.called)

if __name__ == '__main__':
    unittest.main()
