import unittest
import sys
import os
import threading
from unittest.mock import patch, MagicMock, call

# メインアプリケーションのパスを追加
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

# プラットフォーム判定
IS_MACOS = sys.platform == 'darwin'

class TestSystemTray(unittest.TestCase):
    def setUp(self):
        """テストの前準備"""
        self.patcher1 = patch('desktopassistant.macos_rumps_app.pywebview')
        self.patcher2 = patch('desktopassistant.macos_rumps_app.AppHelper')
        self.mock_webview = self.patcher1.start()
        self.mock_app_helper = self.patcher2.start()
        
        # モックウィンドウの設定
        self.mock_window = MagicMock()
        self.mock_webview.windows = []
        self.mock_webview.create_window.return_value = self.mock_window
        
    def tearDown(self):
        """テストのクリーンアップ"""
        self.patcher1.stop()
        self.patcher2.stop()
    
    def test_macos_window_operations(self):
        """macOSウィンドウ操作のテスト"""
        from desktopassistant.macos_rumps_app import MacOSMenuBarApp
        
        # アプリケーションの初期化
        app = MacOSMenuBarApp()
        
        # チャットを開く操作のテスト
        app.open_chat(None)
        
        # ウィンドウが作成され、表示されることを確認
        self.mock_webview.create_window.assert_called_once()
        self.mock_app_helper.callAfter.assert_called_with(self.mock_window.show)
        self.assertIsNotNone(app._window)
        
        # 終了操作のテスト
        app.quit_app(None)
        self.mock_app_helper.callAfter.assert_called_with(self.mock_window.hide)
        self.assertIsNone(app._window)
    
    def test_window_thread_safety(self):
        """ウィンドウ操作のスレッドセーフティテスト"""
        from desktopassistant.macos_rumps_app import MacOSMenuBarApp
        app = MacOSMenuBarApp()
        
        # メインスレッドでの実行テスト
        with patch('threading.current_thread', return_value=threading.main_thread()):
            app._ensure_window_exists()
            self.mock_webview.create_window.assert_called_once()
            self.assertFalse(self.mock_app_helper.callAfter.called)
        
        # 非メインスレッドでの実行テスト
        with patch('threading.current_thread', return_value=MagicMock()):
            self.mock_webview.create_window.reset_mock()
            app._window = None
            app._ensure_window_exists()
            self.assertTrue(self.mock_app_helper.callAfter.called)

if __name__ == '__main__':
    unittest.main()
