from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, SecretStr
import os
import asyncio
import logging
from langchain_aws import ChatBedrock
from typing import List, Tuple
from markdown import markdown
from amazon_transcribe.client import TranscribeStreamingClient
from amazon_transcribe.handlers import TranscriptResultStreamHandler
from amazon_transcribe.model import TranscriptEvent

app = FastAPI()

# Disable CORS. Do not remove this for full-stack development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Initialize Bedrock client
llm = ChatBedrock(
    credentials_profile_name=None,
    region_name="us-east-1",
    model_id="anthropic.claude-3-sonnet-20240229-v1:0",
    model_kwargs={"temperature": 0.7},
)

class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    response: str

@app.get("/healthz")
async def healthz():
    return {"status": "ok"}

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        # 空のメッセージの場合は特別な応答を返す
        if not request.message.strip():
            return ChatResponse(response="申し訳ありません。メッセージを入力してください。")

        messages = [
            (
                "system",
                "あなたは親切なアシスタントです。ユーザーの質問に日本語で答えてください。",
            ),
            ("human", request.message),
        ]
        
        ai_msg = llm.invoke(messages)
        response_text = str(ai_msg.content) if hasattr(ai_msg, 'content') else str(ai_msg)
        # Convert markdown response to HTML
        html_response = markdown(response_text, extensions=['extra'])
        return ChatResponse(response=html_response)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class TranscribeHandler(TranscriptResultStreamHandler):
    """Amazon Transcribeの結果を処理するハンドラー"""
    def __init__(self, output_stream, websocket: WebSocket):
        super().__init__(output_stream)
        self.websocket = websocket
        self.final_transcript = ""
        self.websocket_open = True

    async def handle_transcript_event(self, transcript_event: TranscriptEvent):
        """音声認識結果を処理し、WebSocketを通じてクライアントに送信"""
        if not self.websocket_open:
            return

        results = transcript_event.transcript.results
        for result in results:
            if result.is_partial:
                continue
            for alt in result.alternatives:
                transcript = alt.transcript
                self.final_transcript += transcript + " "
                try:
                    await self.websocket.send_text(transcript)
                except Exception as e:
                    logging.error(f"Error sending transcript: {e}")
                    self.websocket_open = False
                    break

@app.websocket("/TranscribeStreaming")
async def transcribe_streaming(websocket: WebSocket):
    """WebSocketエンドポイント: 音声ストリーミングを受け取り、テキストに変換して返す"""
    await websocket.accept()
    websocket_open = True
    audio_queue = asyncio.Queue()
    
    try:
        # Amazon Transcribeクライアントの初期化
        client = TranscribeStreamingClient(
            region_name="us-east-1",
            language_code="ja-JP"
        )

        # ストリーミングセッションの開始
        stream = await client.start_stream_transcription(
            language_code="ja-JP",
            media_sample_rate_hz=16000,
            media_encoding="pcm"
        )

        # ハンドラーの初期化と非同期タスクの作成
        handler = TranscribeHandler(stream.output_stream, websocket)
        handle_events_task = asyncio.create_task(handler.handle_events())

        async def process_audio():
            """音声データをTranscribeに送信"""
            try:
                while True:
                    chunk = await audio_queue.get()
                    if not chunk:  # 終了シグナル
                        break
                    await stream.input_stream.send_audio_event(audio_chunk=chunk)
            finally:
                await stream.input_stream.end_stream()

        # 音声処理タスクの開始
        process_audio_task = asyncio.create_task(process_audio())

        while websocket_open:
            try:
                # 音声データの受信を待機
                data = await websocket.receive_bytes()
                
                # 終了シグナルの確認
                if not data:
                    break
                    
                # 音声データをキューに追加
                await audio_queue.put(data)
                
            except WebSocketDisconnect:
                logging.info("WebSocket disconnected")
                websocket_open = False
                break

    except Exception as e:
        logging.error(f"Error in transcribe_streaming: {e}")
        if websocket_open:
            await websocket.send_text(f"エラーが発生しました: {str(e)}")
    finally:
        # クリーンアップ処理
        websocket_open = False
        await audio_queue.put(None)  # 終了シグナル
        
        # タスクの終了を待機（存在する場合のみ）
        tasks_to_wait = []
        if 'process_audio_task' in locals() and process_audio_task is not None:
            tasks_to_wait.append(process_audio_task)
        if 'handle_events_task' in locals() and handle_events_task is not None:
            tasks_to_wait.append(handle_events_task)
            
        if tasks_to_wait:
            await asyncio.gather(*tasks_to_wait, return_exceptions=True)
            
        if websocket.client_state.value:
            await websocket.close()
