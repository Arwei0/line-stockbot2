# app.py — 最小 LINE Webhook：把 userId 印到日誌
import os
from flask import Flask, request, abort

from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage, FollowEvent

app = Flask(__name__)

CHANNEL_SECRET = os.environ["LINE_CHANNEL_SECRET"]           # 到 Render 環境變數設定
CHANNEL_ACCESS_TOKEN = os.environ["LINE_CHANNEL_ACCESS_TOKEN"]

line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

@app.route("/healthz")
def healthz():
    return "ok"

@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers.get("X-Line-Signature", "")
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return "OK"

@handler.add(FollowEvent)
def handle_follow(event):
    uid = event.source.user_id
    print(f"[FOLLOW] userId={uid}")  # ← 到 Render Logs 直接看
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text="加好友成功 ✅ 已記錄 userId"))
    # 可選：主動再推一則
    line_bot_api.push_message(uid, TextSendMessage(text="歡迎！你的 userId 已寫入 Logs"))

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    uid = event.source.user_id
    text = event.message.text
    print(f"[MSG] from {uid}: {text}")  # ← Logs 裡也會看到 userId
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"收到訊息～你的 userId：{uid}"))