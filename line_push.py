import requests

def send_line_notify(token: str, message: str):
    if not token or token.startswith("PUT_"):
        print("[WARN] LINE Notify token not set; message would be:\n", message)
        return
    url = "https://notify-api.line.me/api/notify"
    headers = {"Authorization": f"Bearer {token}"}
    data = {"message": message}
    try:
        resp = requests.post(url, headers=headers, data=data, timeout=15)
        if resp.status_code != 200:
            print("[ERROR] LINE Notify push failed:", resp.text)
    except Exception as e:
        print("[ERROR] LINE Notify exception:", e)
