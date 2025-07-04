from flask import Flask, request, abort
import os
import json
import requests

app = Flask(__name__)

CHANNEL_ACCESS_TOKEN = os.getenv("CHANNEL_ACCESS_TOKEN")
CHANNEL_SECRET = os.getenv("CHANNEL_SECRET")

# 記錄每個使用者的狀態
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

def log_history(result_str, point_str, actual_result):
    with open("history_v2.txt", "a", encoding="utf-8") as f:
        f.write(f"{result_str},{point_str},{actual_result}\n")

def predict_next(result_str, point_str):
    p = int(point_str[0])
    b = int(point_str[1])

    if p == b:
        return None

    # 規則 1：最近兩局相同 → 押相反
    if result_str[-1] == result_str[-2]:
        pred = "閒" if result_str[-1] == "莊" else "莊"
    # 規則 2：最近三局交替 → 跟最後一局
    elif (result_str[0] != result_str[1]) and (result_str[1] != result_str[2]):
        pred = result_str[-1]
    # 規則 3：點數差 >= 2 → 押高點數
    elif abs(b - p) >= 2:
        pred = "莊" if b > p else "閒"
    # 規則 4：預設押莊
    else:
        pred = "莊"
    return pred

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
                if clean_text[2] == "和":
                    reply_message(event["replyToken"], "看一把")
                else:
                    user_data[user_id] = {"result_str": clean_text}
                    reply_message(event["replyToken"], "已記錄前三把結果，請輸入下一把的點數")
                continue

            # 處理點數
            if len(clean_text) == 2 and clean_text.isdigit():
                if user_id not in user_data or "result_str" not in user_data[user_id]:
                    reply_message(event["replyToken"], "請先輸入前三把結果（例如：莊閒閒）")
                    continue
                result_str = user_data[user_id]["result_str"]
                prediction = predict_next(result_str, clean_text)
                if prediction is None:
                    reply_message(event["replyToken"], "看一把，請輸入下一把結果")
                else:
                    reply_message(event["replyToken"], prediction)
                    log_history(result_str, clean_text, prediction)
                continue

            # 不合格式
            if user_id not in user_data:
                reply_message(event["replyToken"], "請重新輸入前三把結果（只能用莊閒和組合）")
            else:
                reply_message(event["replyToken"], "請先輸入下一把的點數")

    return "OK"

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
