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

# 初始化資料檔案
def load_history():
    os.makedirs("data", exist_ok=True)
    history_file = "data/history.json"
    if os.path.exists(history_file):
        with open(history_file, encoding="utf-8") as f:
            return json.load(f)
    else:
        return []  # 外層是 list，每一局是 list

def save_history(history):
    with open("data/history.json", "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

@app.route("/callback", methods=['POST'])
def callback():
    body = request.get_json()
    if body is None:
        abort(400)
    events = body.get("events", [])
    history = load_history()
    # 確保至少有一局（如果還沒開始）
    if len(history) == 0:
        history.append([])

    for event in events:
        if event.get("type") == "message" and event["message"]["type"] == "text":
            text = event["message"]["text"].strip().replace(" ", "").replace("-", "")

            # 輸入點數
            if len(text) == 2 and text.isdigit():
                p = int(text[0])
                b = int(text[1])
                if p > b:
                    result = "閒"
                elif p < b:
                    result = "莊"
                else:
                    result = "和"

                # 存到當前局
                history[-1].append({"point": [p, b], "result": result})
                save_history(history)

                reply_message(event["replyToken"], {
                    "type":"text",
                    "text":f"閒{p}，莊{b}"
                })
                continue

            # 輸入結束
            if text == "結束":
                history.append([])  # 開始下一局
                save_history(history)
                reply_message(event["replyToken"], {
                    "type":"text",
                    "text":"本局已結束，請開始下一局。"
                })
                continue

            reply_message(event["replyToken"], {
                "type":"text",
                "text":"請輸入點數（例如84表示閒8莊4）或輸入「結束」"
            })
    return "OK"

@app.route("/history")
def show_history():
    try:
        history = load_history()
        if not history or all(len(game)==0 for game in history):
            content = "目前尚無歷史紀錄。"
        else:
            content = ""
            for idx, game in enumerate(history):
                if len(game) == 0:
                    continue
                content += f"第{idx+1}局：\n"
                content += "\n".join([f"  {h['point']} => {h['result']}" for h in game])
                content += "\n"
    except Exception as e:
        content = f"讀取歷史失敗：{e}"
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
