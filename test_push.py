from linebot import LineBotApi
from linebot.models import TextSendMessage
import os

# 從環境變數拿 LINE access token
CHANNEL_ACCESS_TOKEN = os.getenv("LQDJgnexyskwDiH2nRQge/V0yrXMwNv2XEbFP0wQAL43ma8mgvOWcmydW9RgwE+Jxtlhj59bvppbQvoLPCoBkvzN0JuKWLWmxc1eHQ8EW9de4xYtXtUBRdc1X+o6gaznXZF9w2JqTZlCUqskqKmJaYAdB04t89/1O/w1cDnyilFU=")
line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)

USER_ID = "Ueeb38edab1a74313586d1bc43f792dbe"

line_bot_api.push_message(USER_ID, TextSendMessage(text="測試推播成功！"))
print("推播完成")