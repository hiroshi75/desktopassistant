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
        options = webdriver.ChromeOptions()
        options.add_argument('--no-sandbox')
        options.add_argument('--headless')  # ヘッドレスモードで実行
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--user-data-dir=/tmp/chrome-test-profile')
        self.driver = webdriver.Chrome(options=options)
        self.wait = WebDriverWait(self.driver, 10)
        self.driver.get("http://localhost:8000/chat.html")

    def test_chat_window_elements(self):
        """チャットウィンドウの要素テスト"""
        # 入力フィールドの存在確認
        input_field = self.wait.until(
            EC.presence_of_element_located((By.ID, "input"))
        )
        self.assertTrue(input_field.is_displayed())

        # 送信ボタンの存在確認
        send_button = self.driver.find_element(By.ID, "send")
        self.assertTrue(send_button.is_displayed())

        # チャットエリアの存在確認
        chat_area = self.driver.find_element(By.ID, "chat")
        self.assertTrue(chat_area.is_displayed())

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
