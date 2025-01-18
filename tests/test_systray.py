import unittest
from queue import Queue
import sys
import os

# メインアプリケーションのパスを追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.main import DesktopAssistant

class TestSystemTray(unittest.TestCase):
    def test_event_queue(self):
        """イベントキューのテスト"""
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
