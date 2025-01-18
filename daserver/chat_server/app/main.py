from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, SecretStr
import os
from langchain_aws import ChatBedrock
from typing import List, Tuple

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
    aws_access_key_id=SecretStr(os.environ["AWS_ACCESS_KEY_ID"]),
    aws_secret_access_key=SecretStr(os.environ["AWS_SECRET_ACCESS_KEY"]),
    model="us.amazon.nova-lite-v1:0",
    region="us-east-1",
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
        messages = [
            (
                "system",
                "あなたは親切なアシスタントです。ユーザーの質問に日本語で答えてください。",
            ),
            ("human", request.message),
        ]
        
        ai_msg = llm.invoke(messages)
        response_text = str(ai_msg.content) if hasattr(ai_msg, 'content') else str(ai_msg)
        return ChatResponse(response=response_text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
