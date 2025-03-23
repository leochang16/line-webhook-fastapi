from fastapi import FastAPI, Request

app = FastAPI()

@app.post("/webhook")
async def webhook(request: Request):
    body = await request.json()
    print("Received webhook:", body)
    return {"status": "ok"}
