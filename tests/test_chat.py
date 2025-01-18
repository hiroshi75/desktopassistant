import unittest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import http.server
import threading
import socketserver
import os

class TestChatUI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # HTTPサーバーの設定
        cls.template_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src', 'templates')
        
        class Handler(http.server.SimpleHTTPRequestHandler):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, directory=cls.template_dir, **kwargs)
        
        cls.httpd = socketserver.TCPServer(("", 8000), Handler)
        cls.server_thread = threading.Thread(target=cls.httpd.serve_forever)
        cls.server_thread.daemon = True
        cls.server_thread.start()

    def setUp(self):
        # Seleniumドライバーの設定
        self.driver = webdriver.Chrome()
        self.wait = WebDriverWait(self.driver, 10)
        self.driver.get("http://localhost:8000/chat.html")

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
        cls.httpd.shutdown()
        cls.httpd.server_close()

if __name__ == '__main__':
    unittest.main()
