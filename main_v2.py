from flask import Flask, request, abort
import os
import json
import requests
from datetime import datetime

app = Flask(__name__)

CHANNEL_ACCESS_TOKEN = os.getenv("CHANNEL_ACCESS_TOKEN")
CHANNEL_SECRET = os.getenv("CHANNEL_SECRET")

user_data = {}

def reply_message(reply_token, message_data):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {CHANNEL_ACCESS_TOKEN}"
    }
    data = {
        "replyToken": reply_token,
        "messages": [message_data]
    }
    requests.post("https://api.line.me/v2/bot/message/reply", headers=headers, data=json.dumps(data))

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
            clean_text = text.replace(" ", "").replace("-", "").replace("\n", "")

            # 處理前三把
            if len(clean_text) == 3 and all(c in ["莊", "閒", "和"] for c in clean_text):
                user_data[user_id] = {
                    "current_match": list(clean_text)
                }
                reply_message(event["replyToken"], {"type":"text", "text":"已記錄前三把結果，請輸入下一把點數"})
                continue

            # 處理點數
            if len(clean_text) == 2 and clean_text.isdigit():
                if user_id not in user_data or "current_match" not in user_data[user_id]:
                    reply_message(event["replyToken"], {"type":"text", "text":"請先輸入前三把結果（如：莊閒閒）"})
                    continue
                p = int(clean_text[0])
                b = int(clean_text[1])
                if p == b:
                    result = "和"
                elif p > b:
                    result = "閒"
                else:
                    result = "莊"
                user_data[user_id]["current_match"].append(result)
                reply_message(event["replyToken"], {"type":"text", "text":"已記錄"})
                continue

            # 結束
            if clean_text == "結束":
                if user_id not in user_data or "current_match" not in user_data[user_id]:
                    reply_message(event["replyToken"], {"type":"text", "text":"尚未有對局資料，請先開始一場對局"})
                    continue
                match = user_data[user_id]["current_match"]
                count_z = match.count("莊")
                count_x = match.count("閒")
                count_h = match.count("和")

                # 寫入歷史檔案
                os.makedirs("data", exist_ok=True)
                with open("data/history.txt", "a", encoding="utf-8") as f:
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    f.write(f"{timestamp} : {''.join(match)}\n")

                reply_text = f"對局結束：\n莊：{count_z}\n閒：{count_x}\n和：{count_h}"
                reply_message(event["replyToken"], {"type":"text", "text":reply_text})
                del user_data[user_id]
                continue

            reply_message(event["replyToken"], {"type":"text", "text":"請輸入前三把結果（如：莊閒閒）、點數（如：46）或輸入 結束"})
    return "OK"

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
