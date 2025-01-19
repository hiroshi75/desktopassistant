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

# モジュールをモック化
sys.modules['pywebview'] = mock_webview
sys.modules['PyObjCTools.AppHelper'] = mock_app_helper

# プラットフォーム判定
IS_MACOS = sys.platform == 'darwin'

class TestSystemTray(unittest.TestCase):
    def test_macos_window_operations(self):
        """macOSウィンドウ操作のテスト"""
        # モックウィンドウの設定
        mock_window = MagicMock()
        mock_webview.windows = []
        mock_webview.create_window.return_value = mock_window
        
        from desktopassistant.macos_rumps_app import MacOSMenuBarApp
        app = MacOSMenuBarApp()
        
        # チャットを開く操作のテスト
        app.open_chat(None)
        
        # ウィンドウが作成され、表示されることを確認
        mock_webview.create_window.assert_called_once()
        mock_app_helper.callAfter.assert_called_with(mock_window.show)
        self.assertIsNotNone(app._window)
        
        # 終了操作のテスト
        app.quit_app(None)
        mock_app_helper.callAfter.assert_called_with(mock_window.hide)
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
