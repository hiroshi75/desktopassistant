import unittest
from queue import Queue
import sys
import os
from unittest.mock import patch, MagicMock

# メインアプリケーションのパスを追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class TestSystemTray(unittest.TestCase):
    @patch('desktopassistant.main.get_pystray')
    @patch('desktopassistant.main.VoiceHandler')
    def test_event_queue(self, mock_voice_handler, mock_get_pystray):
        """イベントキューのテスト"""
        # モックpystrayコンポーネントの設定
        mock_icon = MagicMock()
        mock_menu = MagicMock()
        mock_menu_item = MagicMock()
        mock_get_pystray.return_value = (mock_icon, mock_menu, mock_menu_item)
        
        # Import here to avoid early pystray initialization
        from desktopassistant.main import DesktopAssistant
        
        # モックの設定
        mock_voice_handler.return_value.start_background.return_value = MagicMock()
        
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

if __name__ == '__main__':
    unittest.main()
