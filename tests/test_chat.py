import unittest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import threading
import sys
import os

# メインアプリケーションのパスを追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.main import DesktopAssistant

class TestChatApp(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # アプリケーションを別スレッドで起動
        cls.app = DesktopAssistant()
        cls.app_thread = threading.Thread(target=cls.app.run)
        cls.app_thread.daemon = True
        cls.app_thread.start()
        
        # チャットウィンドウを開く
        cls.app.event_queue.put("open_chat")

    def setUp(self):
        # Seleniumドライバーの設定
        self.driver = webdriver.Chrome()
        self.wait = WebDriverWait(self.driver, 10)

    def test_send_message(self):
        """メッセージ送信機能のテスト"""
        # 入力フィールドにメッセージを入力
        input_field = self.wait.until(
            EC.presence_of_element_located((By.ID, "input"))
        )
        input_field.send_keys("テストメッセージ")

        # 送信ボタンをクリック
        send_button = self.driver.find_element(By.ID, "send")
        send_button.click()

        # メッセージが表示されることを確認
        chat_area = self.wait.until(
            EC.presence_of_element_located((By.CLASS_NAME, "user-message"))
        )
        self.assertEqual(chat_area.text, "テストメッセージ")

        # アシスタントの応答が表示されることを確認
        assistant_response = self.wait.until(
            EC.presence_of_element_located((By.CLASS_NAME, "assistant-message"))
        )
        self.assertIn("ご質問ありがとうございます", assistant_response.text)

    def tearDown(self):
        self.driver.quit()

    @classmethod
    def tearDownClass(cls):
        # アプリケーションの終了
        cls.app.event_queue.put("quit")

if __name__ == '__main__':
    unittest.main()
