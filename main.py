from fastapi import FastAPI, Request, UploadFile, File
from fastapi.responses import JSONResponse
from apscheduler.schedulers.background import BackgroundScheduler
from linebot import LineBotApi, WebhookParser
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import os
import requests
import datetime
import pytesseract
from PIL import Image
import shutil

app = FastAPI()

# 初始化 LINE Bot
line_bot_api = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))
parser = WebhookParser(os.getenv("LINE_CHANNEL_SECRET"))
user_id = "U898ccff9df0d7f44eed21ab96821d366"

# 從 symbols.txt 讀取幣種清單
def load_symbols():
    if not os.path.exists("symbols.txt"):
        return ["BTCUSDT", "ETHUSDT"]
    with open("symbols.txt", "r") as f:
        return [line.strip() for line in f.readlines() if line.strip()]

# 偵測爆量下殺邏輯
def check_volume_spike():
    print("[任務啟動] 開始檢查幣種成交量...", datetime.datetime.now())
    symbols_to_track = load_symbols()
    for symbol in symbols_to_track:
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=15m&limit=11"
        response = requests.get(url)
        if response.status_code != 200:
            print(f"無法取得 {symbol} 的資料")
            continue

        klines = response.json()
        volumes = [float(k[5]) for k in klines]  # 成交量在第6欄（index 5）
        last_volume = volumes[-1]
        avg_volume = sum(volumes[:-1]) / 10

        # 價格跌幅計算
        last_close = float(klines[-1][4])  # 最後一根的收盤價
        last_open = float(klines[-1][1])   # 最後一根的開盤價
        price_drop_pct = ((last_open - last_close) / last_open) * 100

        if last_volume > avg_volume * 3:
            print(f"⚠️ 爆量：{symbol} 最新成交量 {last_volume:.2f}，大於平均 {avg_volume:.2f}")
            message = f"🚨🚨🚨: {symbol}\n下跌幅度: {price_drop_pct:.2f}%"
            line_bot_api.push_message(user_id, TextSendMessage(text=message))
        else:
            print(f"{symbol} 沒有爆量 ({last_volume:.2f} / {avg_volume:.2f})")

# 天氣推播邏輯（每天 17:18 發送）
def send_weather():
    print("[任務啟動] 準備發送天氣通知...", datetime.datetime.now())
    try:
        url = "https://api.openweathermap.org/data/2.5/forecast"
        params = {
            "q": "Taipei,tw",
            "appid": "c773b353a06ad4811676f075042f344a",
            "units": "metric",
            "lang": "zh_tw"
        }
        res = requests.get(url, params=params)
        data = res.json()

        if "list" in data:
            forecast = data["list"][0]  # 最近一筆預報資料
            temp_min = forecast["main"]["temp_min"]
            temp_max = forecast["main"]["temp_max"]
            pop = forecast.get("pop", 0) * 100  # 降雨機率（0~1）→ 百分比

            msg = f"📍 台北市今日天氣提醒
降雨機率：{pop:.0f}%
氣溫：{temp_min:.0f}°C - {temp_max:.0f}°C"
            line_bot_api.push_message(user_id, TextSendMessage(text=msg))
        else:
            print("⚠️ 無法解析 OpenWeather 回傳格式")
    except Exception as e:
        print("天氣推播失敗：", e)

# 啟動 APScheduler 定時任務
scheduler = BackgroundScheduler()
scheduler.add_job(check_volume_spike, 'interval', minutes=15)
scheduler.add_job(send_weather, 'cron', hour=17, minute=18)
scheduler.start()

# 上傳圖片並辨識幣種
@app.post("/upload")
async def upload_image(file: UploadFile = File(...)):
    file_location = f"temp_{file.filename}"
    with open(file_location, "wb") as f:
        shutil.copyfileobj(file.file, f)

    image = Image.open(file_location)
    text = pytesseract.image_to_string(image)
    os.remove(file_location)

    lines = text.splitlines()
    symbols = []
    for line in lines:
        parts = line.strip().split()
        for part in parts:
            if part.isalpha() and len(part) <= 6:
                symbols.append(part.upper())

    # 加上 BTC 和 ETH
    final_symbols = list(set([s + "USDT" for s in symbols if len(s) >= 2]))
    final_symbols.extend(["BTCUSDT", "ETHUSDT"])
    final_symbols = list(set(final_symbols))

    with open("symbols.txt", "w") as f:
        for sym in final_symbols:
            f.write(sym + "\n")

    return {"tracked_symbols": final_symbols}

# 手動觸發天氣推播
@app.get("/test-weather")
async def test_weather():
    send_weather()
    return {"message": "已手動執行天氣推播"}

# 手動測試爆量邏輯
@app.get("/test-volume")
async def test_volume():
    check_volume_spike()
    return {"message": "已手動執行爆量檢查"}

# LINE Webhook 端點
@app.post("/webhook")
async def webhook(request: Request):
    signature = request.headers.get("x-line-signature")
    body = await request.body()
    body_text = body.decode("utf-8")

    try:
        events = parser.parse(body_text, signature)
        for event in events:
            if isinstance(event, MessageEvent) and isinstance(event.message, TextMessage):
                user_text = event.message.text
                reply = f"你剛剛說：{user_text}"
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))
                print("使用者傳訊息，userId：", event.source.user_id)
    except Exception as e:
        print("Webhook 發生錯誤：", e)

    return JSONResponse(content={"message": "OK"})
