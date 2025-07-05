from flask import Flask, request, abort, Response
import os
import json
import requests

app = Flask(__name__)

CHANNEL_ACCESS_TOKEN = os.getenv("CHANNEL_ACCESS_TOKEN")
CHANNEL_SECRET = os.getenv("CHANNEL_SECRET")

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
            text = event["message"]["text"].strip().replace(" ", "").replace("-", "")

            # 處理點數輸入
            if len(text) == 2 and text.isdigit():
                p = int(text[0])
                b = int(text[1])
                if p > b:
                    result = "閒"
                elif p < b:
                    result = "莊"
                else:
                    result = "和"

                # 寫入 JSON
                os.makedirs("data", exist_ok=True)
                history_file = "data/history.json"
                if os.path.exists(history_file):
                    with open(history_file, encoding="utf-8") as f:
                        history = json.load(f)
                else:
                    history = []

                history.append({"point": [p, b], "result": result})
                with open(history_file, "w", encoding="utf-8") as f:
                    json.dump(history, f, ensure_ascii=False, indent=2)

                # 只回覆「閒8，莊4」
                reply_message(event["replyToken"], {
                    "type":"text",
                    "text":f"閒{p}，莊{b}"
                })
                continue

            reply_message(event["replyToken"], {
                "type":"text",
                "text":"請輸入點數（例如84表示閒8莊4）"
            })
    return "OK"

@app.route("/history")
def show_history():
    try:
        with open("data/history.json", encoding="utf-8") as f:
            history = json.load(f)
            content = "\n".join([f"{h['point']} => {h['result']}" for h in history])
    except FileNotFoundError:
        content = "目前尚無歷史紀錄。"
    return Response(f"<pre>{content}</pre>", mimetype="text/html")

@app.route("/reset")
def reset_history():
    os.makedirs("data", exist_ok=True)
    with open("data/history.json", "w", encoding="utf-8") as f:
        json.dump([], f)
    return "已清空歷史紀錄。"

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
