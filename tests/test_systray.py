import unittest
from queue import Queue
import sys
import os
from unittest.mock import patch, MagicMock

# macOSではウェイクワード機能を無効化
ENABLE_VOICE_HANDLER = sys.platform != 'darwin'

# メインアプリケーションのパスを追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class TestSystemTray(unittest.TestCase):
    @patch('desktopassistant.main.get_pystray')
    def test_event_queue(self, mock_get_pystray):
        """イベントキューのテスト"""
        # モックpystrayコンポーネントの設定
        mock_icon = MagicMock()
        mock_menu = MagicMock()
        mock_menu_item = MagicMock()
        mock_get_pystray.return_value = (mock_icon, mock_menu, mock_menu_item)
        
        # Import here to avoid early pystray initialization
        from desktopassistant.main import DesktopAssistant
        
        app = DesktopAssistant()
        
        # イベントキューにチャットウィンドウを開くイベントを送信
        app.event_queue.put("open_chat")
        
        # キューにイベントが正しく追加されたことを確認
        event = app.event_queue.get()
        self.assertEqual(event, "open_chat")
        
        # 終了イベントを送信
        app.event_queue.put("quit")
        event = app.event_queue.get()
        self.assertEqual(event, "quit")
        
    @patch('desktopassistant.main.get_pystray')
    @patch('desktopassistant.main.webview')
    def test_macos_window_state(self, mock_webview, mock_get_pystray):
        """macOSウィンドウ状態管理のテスト"""
        # モックの設定
        mock_window = MagicMock()
        mock_window.visible = False
        mock_webview.windows = [mock_window]
        
        mock_icon = MagicMock()
        mock_menu = MagicMock()
        mock_menu_item = MagicMock()
        mock_get_pystray.return_value = (mock_icon, mock_menu, mock_menu_item)
        
        # プラットフォームをmacOSに設定
        with patch('desktopassistant.main.IS_MACOS', True):
            from desktopassistant.main import DesktopAssistant
            app = DesktopAssistant()
            
            # ウィンドウの表示状態を検証
            self.assertFalse(app.verify_window_state(mock_window, False, "initial"))
            
            # ウィンドウを表示
            mock_window.visible = True
            self.assertTrue(app.verify_window_state(mock_window, True, "show"))
            
            # ウィンドウを非表示
            mock_window.visible = False
            self.assertTrue(app.verify_window_state(mock_window, False, "hide"))
            
    @patch('desktopassistant.main.get_pystray')
    @patch('desktopassistant.main.webview')
    def test_macos_menu_initialization(self, mock_webview, mock_get_pystray):
        """macOSメニュー初期化のテスト"""
        # モックの設定
        mock_icon = MagicMock()
        mock_menu = MagicMock()
        mock_menu_item = MagicMock()
        mock_get_pystray.return_value = (mock_icon, mock_menu, mock_menu_item)
        
        # プラットフォームをmacOSに設定
        with patch('desktopassistant.main.IS_MACOS', True), \
             patch('desktopassistant.main.AppKit') as mock_appkit, \
             patch('desktopassistant.main.AppHelper') as mock_apphelper:
            
            # AppKitモックの設定
            mock_menu = MagicMock()
            mock_menu_item = MagicMock()
            mock_app = MagicMock()
            
            mock_appkit.NSMenu.alloc.return_value.init.return_value = mock_menu
            mock_appkit.NSMenuItem.alloc.return_value.init.return_value = mock_menu_item
            mock_appkit.NSApplication.sharedApplication.return_value = mock_app
            
            from desktopassistant.main import DesktopAssistant
            app = DesktopAssistant()
            
            # メニューが正しく初期化されたことを確認
            mock_menu.setTitle_.assert_called_with("デスクトップアシスタント")
            mock_app.setMainMenu_.assert_called_with(mock_menu)
            
            # メニュー項目が追加されたことを確認
            self.assertTrue(mock_menu.insertItem_atIndex_.called)
            self.assertTrue(mock_menu_item.setSubmenu_.called)
            
    @patch('desktopassistant.main.get_pystray')
    @patch('desktopassistant.main.webview')
    @patch('threading.current_thread')
    def test_thread_safety(self, mock_current_thread, mock_webview, mock_get_pystray):
        """スレッドセーフティのテスト"""
        # モックの設定
        mock_icon = MagicMock()
        mock_menu = MagicMock()
        mock_menu_item = MagicMock()
        mock_get_pystray.return_value = (mock_icon, mock_menu, mock_menu_item)
        
        mock_window = MagicMock()
        mock_webview.windows = [mock_window]
        
        # メインスレッドの設定
        main_thread = MagicMock()
        mock_current_thread.return_value = main_thread
        
        # プラットフォームをmacOSに設定
        with patch('desktopassistant.main.IS_MACOS', True), \
             patch('desktopassistant.main.AppHelper') as mock_apphelper:
            
            from desktopassistant.main import DesktopAssistant
            app = DesktopAssistant()
            
            # メインスレッドでの実行をテスト
            test_func = MagicMock()
            main_thread.return_value = True
            app.execute_on_main_thread(test_func)
            
            # メインスレッドでは直接実行されることを確認
            test_func.assert_called_once()
            self.assertFalse(mock_apphelper.callAfter.called)
            
            # 非メインスレッドでの実行をテスト
            test_func.reset_mock()
            main_thread.return_value = False
            
            app.execute_on_main_thread(test_func)
            
            # AppHelper.callAfterが使用されることを確認
            mock_apphelper.callAfter.assert_called_once()
            
            # システムトレイの初期化が別スレッドで行われることを確認
            tray_icon = app.setup_tray_icon()
            self.assertIsNotNone(tray_icon)
            
            # WebViewの操作がメインスレッドで実行されることを確認
            window = mock_webview.windows[0]
            
            def show_window():
                window.show()
            
            app.execute_on_main_thread(show_window)
            window.show.assert_called_once()

    @patch('desktopassistant.main.IS_MACOS', True)
    @patch('desktopassistant.main.get_pystray')
    @patch('desktopassistant.main.webview')
    def test_macos_tray_click_opens_chat(self, mock_webview, mock_get_pystray):
        """macOSでのトレイメニュークリックのテスト"""
        # モックの設定
        mock_window = MagicMock()
        mock_window.visible = False
        mock_webview.windows = [mock_window]
        
        mock_icon = MagicMock()
        mock_menu = MagicMock()
        mock_menu_item = MagicMock()
        mock_get_pystray.return_value = (mock_icon, mock_menu, mock_menu_item)
        
        # アプリケーションの初期化
        from desktopassistant.main import DesktopAssistant
        app = DesktopAssistant()
        
        # トレイアイコンのセットアップ
        tray_icon = app.setup_tray_icon()
        
        # メニューアイテムのクリックをシミュレート
        menu_items = [item for item in tray_icon.menu]
        open_chat_item = next(item for item in menu_items if "チャットを開く" in str(item))
        open_chat_item(mock_icon)
        
        # イベントキューを確認
        event = app.event_queue.get_nowait()
        self.assertEqual(event, "open_chat")
        
        # イベントの処理をシミュレート
        app.window_manager(mock_window)
        
        # ウィンドウの状態を検証
        self.assertTrue(mock_window.show.called)
        self.assertTrue(getattr(mock_window, 'visible', False))

if __name__ == '__main__':
    unittest.main()
