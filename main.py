from flask import Flask, request, abort
import os
import json
import requests

app = Flask(__name__)

CHANNEL_ACCESS_TOKEN = os.getenv("CHANNEL_ACCESS_TOKEN")
CHANNEL_SECRET = os.getenv("CHANNEL_SECRET")

# 使用者狀態記錄
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
    # 簡單示例邏輯
    if "閒閒" in result_str:
        return "莊"
    p = int(point_str[0])
    b = int(point_str[1])
    return "莊" if b > p else "閒"

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

            # 去除空白、破折號、換行
            clean_text = text.replace(" ", "").replace("-", "").replace("\n", "")

            # 如果是三個字符，且都是莊閒和
            if len(clean_text) == 3 and all(c in ["莊", "閒", "和"] for c in clean_text):
                if clean_text[2] == "和":
                    reply_message(event["replyToken"], "看一把")
                else:
                    user_data[user_id] = {"result_str": clean_text}
                    reply_message(event["replyToken"], "已記錄前三把結果，請輸入下一把的點數")
                continue

            # 如果輸入是2位數字點數
            if len(clean_text) == 2 and clean_text.isdigit():
                if user_id not in user_data or "result_str" not in user_data[user_id]:
                    reply_message(event["replyToken"], "請先輸入前三把結果（例如：莊閒閒）")
                    continue
                result_str = user_data[user_id]["result_str"]
                prediction = predict_next(result_str, clean_text)
                reply_message(event["replyToken"], prediction)
                continue

            # 如果一開始就不是莊閒和組合的三個字
            if user_id not in user_data:
                reply_message(event["replyToken"], "請重新輸入前三把結果（只能用莊閒和組合）")
            else:
                reply_message(event["replyToken"], "請先輸入下一把的點數（例如：46）")

    return "OK"

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
