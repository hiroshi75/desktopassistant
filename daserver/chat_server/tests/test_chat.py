import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_healthz():
    """ヘルスチェックエンドポイントのテスト"""
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_chat_endpoint():
    """チャットエンドポイントの基本的な機能テスト"""
    test_message = "こんにちは"
    response = client.post(
        "/chat",
        json={"message": test_message}
    )
    
    # ステータスコードの確認
    assert response.status_code == 200
    
    # レスポンスの構造の確認
    response_data = response.json()
    assert "response" in response_data
    assert isinstance(response_data["response"], str)
    assert len(response_data["response"]) > 0

def test_chat_endpoint_empty_message():
    """空のメッセージを送信した場合のテスト"""
    response = client.post(
        "/chat",
        json={"message": ""}
    )
    
    # ステータスコードの確認
    assert response.status_code == 200
    
    # レスポンスの構造の確認
    response_data = response.json()
    assert "response" in response_data
    assert isinstance(response_data["response"], str)

def test_chat_endpoint_invalid_request():
    """不正なリクエストボディのテスト"""
    response = client.post(
        "/chat",
        json={"invalid_key": "こんにちは"}
    )
    
    # 不正なリクエストなので400が返されることを確認
    assert response.status_code == 422
