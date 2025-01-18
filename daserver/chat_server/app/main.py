from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, SecretStr
import os
import asyncio
import logging
import time

# ログレベルの設定
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(levelname)s - %(message)s')
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

# Initialize Bedrock client with AWS credentials from environment variables
llm = ChatBedrock(
    model="anthropic.claude-3-sonnet-20240229-v1:0",
    region=os.getenv('AWS_REGION', 'us-east-1'),
    aws_access_key_id=SecretStr(os.getenv('AWS_ACCESS_KEY_ID', '')),
    aws_secret_access_key=SecretStr(os.getenv('AWS_SECRET_ACCESS_KEY', '')),
    model_kwargs={"temperature": 0.7}
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
    def __init__(self, output_stream, websocket: WebSocket, llm: ChatBedrock):
        super().__init__(output_stream)
        self.websocket = websocket
        self.final_transcript = ""
        self.websocket_open = True
        self.llm = llm
        logging.info("TranscribeHandlerが初期化されました")
        
    async def handle_events(self):
        """イベントの処理を開始"""
        logging.info("handle_eventsを開始します")
        try:
            logging.info("Amazon Transcribeからの応答待機中...")
            await super().handle_events()
            logging.info("Amazon Transcribeからの応答受信完了")
        except Exception as e:
            logging.error(f"handle_eventsでエラーが発生: {e}")
            logging.error(f"エラーの詳細: {str(e.__class__.__name__)}: {str(e)}")
            self.websocket_open = False
        finally:
            logging.info("handle_eventsが終了しました")

    async def process_with_llm(self, text: str):
        """テキストをLLMで処理し、応答を返す"""
        try:
            messages = [
                (
                    "system",
                    "あなたは親切なアシスタントです。ユーザーの音声入力に対して日本語で簡潔に答えてください。",
                ),
                ("human", text),
            ]
            
            ai_msg = self.llm.invoke(messages)
            response_text = str(ai_msg.content) if hasattr(ai_msg, 'content') else str(ai_msg)
            # マークダウンをHTMLに変換
            html_response = markdown(response_text, extensions=['extra'])
            
            if self.websocket_open:
                await self.websocket.send_text(f"応答: {html_response}")
        except Exception as e:
            logging.error(f"Error processing LLM response: {e}")
            if self.websocket_open:
                await self.websocket.send_text(f"LLM処理エラー: {str(e)}")

    async def handle_transcript_event(self, transcript_event: TranscriptEvent):
        """音声認識結果を処理し、WebSocketを通じてクライアントに送信"""
        if not self.websocket_open:
            return

        try:
            if not hasattr(transcript_event, 'transcript') or not transcript_event.transcript:
                logging.debug("TranscriptEventにtranscriptプロパティがありません")
                return

            results = transcript_event.transcript.results
            if not results:
                logging.debug("音声認識結果が空です")
                return

            for result in results:
                if not hasattr(result, 'alternatives') or not result.alternatives:
                    logging.debug("代替テキストが見つかりません")
                    continue

                if hasattr(result, 'is_partial') and result.is_partial:
                    logging.debug("部分的な結果をスキップします")
                    continue

                for alt in result.alternatives:
                    if not hasattr(alt, 'transcript'):
                        logging.debug("代替テキストにtranscriptプロパティがありません")
                        continue

                    transcript = alt.transcript.strip()
                    if transcript:
                        logging.info(f"認識されたテキスト: {transcript}")
                        self.final_transcript += transcript + " "
                        if self.websocket_open:
                            await self.websocket.send_text(f"認識テキスト: {transcript}")
                            await self.process_with_llm(transcript)

        except Exception as e:
            logging.error(f"TranscriptEvent処理中にエラーが発生しました: {e}")
            self.websocket_open = False

    async def send_final_transcript(self):
        """最終的な認識テキストを送信"""
        if self.websocket_open and self.final_transcript.strip():
            try:
                await self.websocket.send_text(f"最終認識テキスト: {self.final_transcript.strip()}")
            except Exception as e:
                logging.error(f"最終テキスト送信中にエラーが発生しました: {e}")
                self.websocket_open = False

@app.websocket("/TranscribeStreaming")
async def transcribe_streaming(websocket: WebSocket):
    """WebSocketエンドポイント: 音声ストリーミングを受け取り、テキストに変換して返す"""
    await websocket.accept()
    websocket_open = True
    stop_audio_stream = False
    audio_queue = asyncio.Queue()
    
    # タイムアウトを設定（60秒）
    websocket.client.timeout = 60.0
    
    try:
        # Amazon Transcribeクライアントの初期化
        logging.info("Amazon Transcribeクライアントを初期化中...")
        client = TranscribeStreamingClient(region=os.getenv('AWS_REGION', 'us-east-1'))
        logging.info("Amazon Transcribeクライアントの初期化が完了しました")

        # ストリーミングセッションの開始
        logging.info("ストリーミングセッションを開始します...")
        # ストリーミングセッションの開始（基本パラメータのみ）
        # Amazon Transcribeの設定をデバッグ出力
        logging.debug("TranscribeStreamingClient設定:")
        logging.debug(f"- 言語コード: ja-JP")
        logging.debug(f"- サンプリングレート: 8000 Hz")
        logging.debug(f"- エンコーディング: pcm")
        logging.debug(f"- リージョン: {os.getenv('AWS_REGION', 'us-east-1')}")
        
        # ストリーミングセッションの開始（タイムアウトと安定性の設定を追加）
        stream = await client.start_stream_transcription(
            language_code="ja-JP",
            media_sample_rate_hz=16000,
            media_encoding="pcm",
            session_id=f"session-{int(time.time())}",  # セッションIDを追加
            enable_partial_results_stabilization=True,  # 部分的な結果の安定化を有効化
            partial_results_stability="high",  # 高い安定性を設定
            show_speaker_label=False,  # スピーカーラベルは不要
            max_real_time_factor=3  # リアルタイムの3倍まで許容（タイムアウト対策）
        )
        # AWS認証情報の確認
        logging.debug("AWS認証情報の確認:")
        logging.debug(f"- リージョン: {os.getenv('AWS_REGION', 'us-east-1')}")
        logging.debug(f"- アクセスキーID: {'設定済み' if os.getenv('AWS_ACCESS_KEY_ID') else '未設定'}")
        logging.debug(f"- シークレットキー: {'設定済み' if os.getenv('AWS_SECRET_ACCESS_KEY') else '未設定'}")

        # ストリーム設定の確認
        # ストリーム処理のデバッグログを追加
        logging.debug("ストリーム情報:")
        logging.debug(f"- 入力ストリーム: {stream.input_stream}")
        logging.debug(f"- 出力ストリーム: {stream.output_stream}")
        logging.info("ストリーミングセッションが開始されました")

        # ハンドラーの初期化
        handler = TranscribeHandler(stream.output_stream, websocket, llm)

        async def mic_stream():
            """音声データのストリーミング"""
            while True:
                try:
                    chunk = await audio_queue.get()
                    if stop_audio_stream or not chunk:
                        break
                    
                    # チャンクサイズとデータ形式を確認
                    chunk_size = len(chunk)
                    logging.debug(f"音声チャンクの処理:")
                    logging.debug(f"- チャンクサイズ: {chunk_size} バイト")
                    logging.debug(f"- データタイプ: {type(chunk)}")
                    
                    if chunk_size > 0:
                        # PCMデータとしてチャンクを送信
                        # Amazon Transcribeは16kHz、16ビット、モノラルPCMを期待
                        yield chunk, None
                    else:
                        logging.warning("空のチャンクをスキップします")
                        continue
                        
                except Exception as e:
                    logging.error(f"音声ストリーミングエラー: {e}")
                    break
                
                # チャンク間に小さな遅延を入れる
                await asyncio.sleep(0.01)

        async def write_chunks(stream):
            """音声チャンクの送信"""
            chunk_count = 0
            total_bytes = 0
            
            async for chunk, _ in mic_stream():
                try:
                    chunk_count += 1
                    total_bytes += len(chunk)
                    logging.info(f"チャンク {chunk_count} を送信中 (合計: {total_bytes} バイト)")
                    
                    # 音声データをTranscribeに送信
                    await stream.input_stream.send_audio_event(audio_chunk=chunk)
                    logging.debug(f"チャンク {chunk_count} の送信完了")
                    
                    # ストリームの状態を確認
                    if hasattr(stream, 'status'):
                        logging.debug(f"ストリーム状態: {stream.status}")
                    
                except OSError as e:
                    logging.error(f"OSError in write_chunks: {e}")
                    break
                except Exception as e:
                    logging.error(f"予期せぬエラー in write_chunks: {e}")
                    break
                    
                # 短い遅延を入れてCPU使用率を抑える
                await asyncio.sleep(0.01)
            
            logging.info("すべてのチャンクの送信が完了しました")
            await stream.input_stream.end_stream()
            logging.info("ストリームを終了しました")

        # 非同期タスクの作成と開始
        send_task = asyncio.create_task(write_chunks(stream))
        handle_task = asyncio.create_task(handler.handle_events())

        while websocket_open:
            try:
                # メッセージの受信を待機
                message = await websocket.receive()
                logging.info(f"受信メッセージタイプ: {message.get('type')}")

                if message["type"] == "websocket.receive":
                    if "bytes" in message:
                        audio_chunk = message["bytes"]
                        logging.info(f"音声データを受信しました（サイズ: {len(audio_chunk)}バイト）")
                        await audio_queue.put(audio_chunk)
                    elif "text" in message:
                        text_message = message["text"]
                        logging.info(f"テキストメッセージを受信: {text_message}")
                        if text_message == "submit_response":
                            logging.info("音声入力の終了シグナルを受信")
                            stop_audio_stream = True
                            try:
                                # 残りの音声データを処理
                                await asyncio.wait_for(send_task, timeout=5.0)
                                # ストリームを明示的に終了
                                await stream.input_stream.end_stream()
                                logging.info("音声ストリームを終了しました")
                                # 最終的な認識結果を待機
                                await handler.send_final_transcript()
                                # 正常な終了を通知
                                await websocket.send_text("処理完了")
                            except asyncio.TimeoutError:
                                logging.error("音声データの処理がタイムアウトしました")
                                await websocket.send_text("エラー: 処理がタイムアウトしました")
                            except Exception as e:
                                logging.error(f"音声データの処理中にエラーが発生: {e}")
                                await websocket.send_text(f"エラー: {str(e)}")
                            finally:
                                break

            except WebSocketDisconnect:
                logging.info("WebSocket disconnected")
                websocket_open = False
                break

    except Exception as e:
        logging.error(f"Error in transcribe_streaming: {e}")
        try:
            if websocket_open and websocket.client_state and websocket.client_state.value != 3:  # 3 = DISCONNECTED
                await websocket.send_text(f"エラーが発生しました: {str(e)}")
        except Exception as ws_error:
            logging.error(f"Error sending error message: {ws_error}")
    finally:
        # クリーンアップ処理
        websocket_open = False
        stop_audio_stream = True
        
        try:
            await audio_queue.put(None)  # 終了シグナル
            
            # タスクの終了を待機（タスクが存在する場合のみ）
            if 'send_task' in locals() and 'handle_task' in locals():
                tasks_to_wait = [send_task, handle_task]
                await asyncio.gather(*tasks_to_wait, return_exceptions=True)
        except Exception as cleanup_error:
            logging.error(f"Error during task cleanup: {cleanup_error}")
        
        # WebSocketの状態を確認してから閉じる
        try:
            if websocket.client_state and websocket.client_state.value != 3:  # 3 = DISCONNECTED
                await websocket.close()
        except Exception as ws_error:
            logging.error(f"Error during WebSocket cleanup: {ws_error}")
            pass  # 既に閉じている場合は無視
