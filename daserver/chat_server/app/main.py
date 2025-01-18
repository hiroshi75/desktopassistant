from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, SecretStr
import os
from langchain_aws import ChatBedrock
from typing import List, Tuple
from markdown import markdown

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
