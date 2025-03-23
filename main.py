from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from linebot import LineBotApi, WebhookParser
from linebot.models import MessageEvent, TextMessage
import os

app = FastAPI()

# 用你的 LINE Access Token & Secret，放在 Render 的環境變數
line_bot_api = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))
parser = WebhookParser(os.getenv("LINE_CHANNEL_SECRET"))

@app.post("/webhook")
async def webhook(request: Request):
    signature = request.headers["x-line-signature"]
    body = await request.body()
    body_text = body.decode("utf-8")

    events = parser.parse(body_text, signature)
    for event in events:
        if isinstance(event, MessageEvent) and isinstance(event.message, TextMessage):
            print("你的 userId 是：", event.source.user_id)

    return JSONResponse(content={"message": "OK"})
