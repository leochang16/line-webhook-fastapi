from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from linebot import LineBotApi, WebhookParser
from linebot.models import MessageEvent, TextMessage
import os

app = FastAPI()

# 用你的 LINE Access Token & Secret，放在 Render 的環境變數
line_bot_api = LineBotApi(os.getenv("BlBltEYqeTSJgswfQV2fHPdG8qrd7o1pgGuOsCQui22JZ6nRwYOp4ViqXPcOVdV76tCAAijz4lpT/ZM5trYbvAfOMkM8a1VIZZJYQd1saF5a53S6m5Lw0+nt2GJTDkak0xUGjPDN2/vSPvLGbCmIdAdB04t89/1O/w1cDnyilFU="))
parser = WebhookParser(os.getenv("d663a339be4145ec663a312dea25c5b1"))

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
