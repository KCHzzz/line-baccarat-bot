from flask import Flask, request, abort
import os
import json
import requests

app = Flask(__name__)

CHANNEL_ACCESS_TOKEN = os.getenv("CHANNEL_ACCESS_TOKEN")
CHANNEL_SECRET = os.getenv("CHANNEL_SECRET")

# 每位用戶的對局資料
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

def save_match(user_id):
    match = user_data.get(user_id, {}).get("current_match", [])
    with open("matches.txt", "a", encoding="utf-8") as f:
        f.write(",".join(match) + "\n")

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

            # 處理前三把結果
            if len(clean_text) == 3 and all(c in ["莊", "閒", "和"] for c in clean_text):
                user_data[user_id] = {
                    "result_str": clean_text,
                    "current_match": list(clean_text)  # 從前三把開始記錄
                }
                reply_message(event["replyToken"], "已記錄前三把結果，請輸入下一把點數")
                continue

            # 處理點數
            if len(clean_text) == 2 and clean_text.isdigit():
                if user_id not in user_data or "current_match" not in user_data[user_id]:
                    reply_message(event["replyToken"], "請先輸入前三把結果（例如：莊閒閒）")
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
                reply_message(event["replyToken"], "已記錄")
                continue

            # 處理結束
            if clean_text == "結束":
                if user_id not in user_data or "current_match" not in user_data[user_id]:
                    reply_message(event["replyToken"], "尚未有對局資料，請先開始一場對局")
                    continue
                match = user_data[user_id]["current_match"]
                count_b = match.count("莊")
                count_p = match.count("閒")
                count_t = match.count("和")
                reply_message(event["replyToken"], f"從前三把到現在的統計：\n莊：{count_b}\n閒：{count_p}\n和：{count_t}")
                save_match(user_id)
                del user_data[user_id]
                continue

            # 不符合格式
            reply_message(event["replyToken"], "請輸入前三把結果（例如：莊閒閒）、點數（例如：46）或輸入 結束")
    return "OK"

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
