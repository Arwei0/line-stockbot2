from linebot import LineBotApi
from linebot.models import TextSendMessage
import sys
sys.stdout.reconfigure(encoding='utf-8')

# 把這裡換成你 LINE Developers 後台的 Channel access token (長長的一串字)
CHANNEL_ACCESS_TOKEN = "你的ChannelAccessToken"

# 這裡換成你自己的 UserId（像 Ueeb38edab1a74313586d1bc43f792dbe）
USER_ID = "你的UserId"

line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
line_bot_api.push_message(USER_ID, TextSendMessage(text="Hello from test_push.py!"))

print("測試訊息已送出！")