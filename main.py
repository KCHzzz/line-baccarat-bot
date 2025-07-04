from flask import Flask, request, abort
import os
import json
import requests

app = Flask(__name__)

CHANNEL_ACCESS_TOKEN = os.getenv("CHANNEL_ACCESS_TOKEN")
CHANNEL_SECRET = os.getenv("CHANNEL_SECRET")

# 簡單記憶體儲存，每個 user 的狀態
user_data = {}

def reply_message(reply_token, text):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {CHANNEL_ACCESS_TOKEN}"
    }
    data = {
        "replyToken": reply_token,
        "messages": [{"type": "text", "text": text}]
    }
    requests.post("https://api.line.me/v2/bot/message/reply", headers=headers, data=json.dumps(data))

def predict_next(result_str, point_str):
    # result_str 例如 "莊閒閒"
    # point_str 例如 "46" (閒4 莊6)

    # 簡單邏輯示範：
    if "閒閒" in result_str:
        return "莊"
    if len(point_str) != 2 or not point_str.isdigit():
        return "閒"  # 預設
    p = int(point_str[0])
    b = int(point_str[1])
    if b > p:
        return "莊"
    else:
        return "閒"

@app.route("/callback", methods=['POST'])
def callback():
    body = request.get_json()
    if body is None:
        abort(400)
    events = body.get("events", [])
    for event in events:
        if event.get("type") == "message" and event["message"]["type"] == "text":
            user_id = event["source"]["userId"]
            text = event["message"]["text"].strip()

            # 判斷是否是前三把結果(只含莊閒，長度3)
            if len(text) == 3 and all(c in ["莊", "閒"] for c in text):
                # 重設該使用者狀態
                user_data[user_id] = {"result_str": text}
                reply_message(event["replyToken"], "請輸入下一把的點數")
                continue

            # 判斷是否是點數輸入(長度2純數字)
            if len(text) == 2 and text.isdigit():
                if user_id not in user_data or "result_str" not in user_data[user_id]:
                    reply_message(event["replyToken"], "請先輸入前三把結果（例如：莊閒閒）")
                    continue
                result_str = user_data[user_id]["result_str"]
                pred = predict_next(result_str, text)
                reply_message(event["replyToken"], pred)
                continue

            # 其他情況
            reply_message(event["replyToken"], "請先輸入前三把結果（例如：莊閒閒），或輸入兩位數點數（例如：46）")

    return "OK"

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
