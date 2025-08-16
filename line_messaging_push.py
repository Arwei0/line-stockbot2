# line_messaging_push.py — LINE Messaging API 主動推播
import requests
import json

def _load_cfg(config_path="config.json"):
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)

def push_message(text: str, config_path: str = "config.json"):
    """將文字訊息推播給 config.json/messaging_api/recipients 列表"""
    cfg = _load_cfg(config_path).get("messaging_api", {})
    token = cfg.get("channel_access_token")
    recipients = cfg.get("recipients", [])
    if not token or not recipients:
        print("[WARN] Messaging API 未設定（channel_access_token 或 recipients），略過推播。")
        return

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    url = "https://api.line.me/v2/bot/message/push"

    for uid in recipients:
        body = {"to": uid, "messages": [{"type": "text", "text": text}]}
        try:
            r = requests.post(url, headers=headers, json=body, timeout=15)
            if r.status_code != 200:
                print(f"[ERROR] LINE push 失敗 uid={uid}: {r.status_code} {r.text}")
        except Exception as e:
            print(f"[ERROR] LINE push 例外 uid={uid}: {e}")