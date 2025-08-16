from linebot import LineBotApi
from linebot.models import TextSendMessage
import os

# 從環境變數拿 LINE access token
CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)

USER_ID = "Ueeb38edab1a74313586d1bc43f792dbe"

line_bot_api.push_message(USER_ID, TextSendMessage(text="測試推播成功！"))
print("推播完成")