import pytest
from fastapi.testclient import TestClient
from fastapi.websockets import WebSocket, WebSocketDisconnect
import asyncio
from app.main import app
from unittest.mock import AsyncMock, MagicMock, patch
import json

client = TestClient(app)

# WebSocketテスト用のフィクスチャ
@pytest.fixture
def test_websocket():
    return AsyncMock(spec=WebSocket)

@pytest.fixture
def mock_transcribe_client():
    with patch('app.main.TranscribeStreamingClient') as mock_client:
        # モックストリームの設定
        mock_stream = AsyncMock()
        mock_stream.output_stream = AsyncMock()
        mock_stream.input_stream = AsyncMock()
        mock_stream.input_stream.send_audio_event = AsyncMock()
        mock_stream.input_stream.end_stream = AsyncMock()
        
        # モッククライアントの設定
        mock_client.return_value.start_stream_transcription = AsyncMock(
            return_value=mock_stream
        )
        
        yield mock_client

@pytest.fixture
def mock_llm():
    with patch('app.main.llm') as mock:
        mock.invoke = MagicMock(return_value=MagicMock(
            content="テストレスポンス"
        ))
        yield mock

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

@pytest.mark.asyncio
async def test_transcribe_streaming(test_websocket, mock_transcribe_client, mock_llm):
    """音声認識WebSocketエンドポイントのテスト"""
    from app.main import transcribe_streaming
    import asyncio
    
    # モックストリームの設定
    mock_stream = AsyncMock()
    mock_stream.output_stream = AsyncMock()
    mock_stream.input_stream = AsyncMock()
    mock_stream.input_stream.send_audio_event = AsyncMock()
    mock_stream.input_stream.end_stream = AsyncMock()
    
    # モッククライアントの設定
    mock_transcribe_client.return_value = AsyncMock()
    mock_transcribe_client.return_value.start_stream_transcription = AsyncMock(
        return_value=mock_stream
    )
    
    # WebSocketの接続とメッセージ受信をシミュレート
    test_websocket.accept = AsyncMock()
    test_websocket.receive = AsyncMock()
    test_websocket.send_text = AsyncMock()
    test_websocket.close = AsyncMock()
    test_websocket.client_state = MagicMock()
    test_websocket.client_state.value = 1  # 接続中の状態をシミュレート
    
    # メッセージのシーケンスを設定
    messages = [
        {"type": "websocket.receive", "bytes": b"test_audio_data"},
        {"type": "websocket.receive", "text": "submit_response"}
    ]
    
    async def mock_receive():
        await asyncio.sleep(0.1)  # メッセージ処理の遅延をシミュレート
        if not messages:
            raise WebSocketDisconnect()
        return messages.pop(0)
    
    test_websocket.receive.side_effect = mock_receive
    
    # エンドポイントを実行
    async def run_endpoint():
        try:
            await transcribe_streaming(test_websocket)
        except WebSocketDisconnect:
            pass
    
    # タイムアウト付きでエンドポイントを実行
    endpoint_task = asyncio.create_task(run_endpoint())
    
    # メッセージ処理を待つ
    await asyncio.sleep(1.0)  # 十分な時間を確保
    
    # WebSocketの接続が確立されたことを確認
    test_websocket.accept.assert_called_once()
    
    # TranscribeClientが正しく初期化されたことを確認
    mock_transcribe_client.assert_called_once()
    mock_transcribe_client.return_value.start_stream_transcription.assert_called_once_with(
        language_code="ja-JP",
        media_sample_rate_hz=8000,
        media_encoding="pcm"
    )
    
    # 音声データが正しく処理されたことを確認
    assert mock_stream.input_stream.send_audio_event.called, "send_audio_eventが呼び出されていません"
    mock_stream.input_stream.send_audio_event.assert_called_with(
        audio_chunk=b"test_audio_data"
    )
    
    # タスクをキャンセルしてクリーンアップ
    endpoint_task.cancel()
    try:
        await endpoint_task
    except (asyncio.CancelledError, WebSocketDisconnect):
        pass
    
    # WebSocketが正しく閉じられたことを確認
    assert test_websocket.close.called

@pytest.mark.asyncio
async def test_transcribe_handler(test_websocket, mock_llm):
    """TranscribeHandlerのテスト"""
    from app.main import TranscribeHandler
    from amazon_transcribe.model import TranscriptEvent
    
    # ハンドラーの初期化
    handler = TranscribeHandler(AsyncMock(), test_websocket, mock_llm)
    handler.websocket_open = True  # 明示的にwebsocket_openフラグを設定
    
    # テスト用の音声認識結果を作成（実際のAmazon Transcribeの応答形式に合わせる）
    # TranscriptEventのモックを作成
    mock_event = AsyncMock(spec=TranscriptEvent)
    mock_event.transcript = MagicMock()
    
    # 結果オブジェクトの作成
    result = MagicMock()
    result.is_partial = False
    
    # 代替テキストオブジェクトの作成
    alt = MagicMock()
    alt.transcript = "こんにちは"
    
    # 結果オブジェクトに代替テキストを設定
    result.alternatives = [alt]
    
    # トランスクリプトに結果を設定
    mock_event.transcript.results = [result]
    
    # イベント処理を実行
    await handler.handle_transcript_event(mock_event)
    
    # 認識テキストが送信されたことを確認
    test_websocket.send_text.assert_any_call("認識テキスト: こんにちは")
    
    # LLMが呼び出されたことを確認
    mock_llm.invoke.assert_called_once()
    
    # LLMの応答が送信されたことを確認（HTMLタグを含む形式）
    test_websocket.send_text.assert_any_call("応答: <p>テストレスポンス</p>")
