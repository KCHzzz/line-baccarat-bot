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

# 載入新的資料庫
def load_games():
    os.makedirs("data", exist_ok=True)
    file_path = "data/games.json"
    if os.path.exists(file_path):
        with open(file_path, encoding="utf-8") as f:
            return json.load(f)
    else:
        return []

def save_games(games):
    with open("data/games.json", "w", encoding="utf-8") as f:
        json.dump(games, f, ensure_ascii=False, indent=2)

@app.route("/callback", methods=['POST'])
def callback():
    body = request.get_json()
    if body is None:
        abort(400)
    events = body.get("events", [])
    games = load_games()

    for event in events:
        if event.get("type") == "message" and event["message"]["type"] == "text":
            text = event["message"]["text"].strip().replace(" ", "").replace("-", "")

            # 檢查是否只包含莊閒和
            if all(c in "莊閒和" for c in text) and len(text) > 0:
                game_result = list(text)
                games.append(game_result)
                save_games(games)

                # 統計
                banker = game_result.count("莊")
                player = game_result.count("閒")
                tie = game_result.count("和")

                reply_message(event["replyToken"], {
                    "type":"text",
                    "text":f"莊：{banker} 閒：{player} 和：{tie}"
                })
                continue

            reply_message(event["replyToken"], {
                "type":"text",
                "text":"請輸入整局結果（例如 莊莊閒和莊閒）"
            })
    return "OK"

@app.route("/games")
def show_games():
    try:
        games = load_games()
        if not games:
            content = "目前尚無歷史紀錄。"
        else:
            content = ""
            for idx, game in enumerate(games):
                content += f"第{idx+1}局：{' '.join(game)}\n"
    except Exception as e:
        content = f"讀取失敗：{e}"
    return Response(f"<pre>{content}</pre>", mimetype="text/html")

@app.route("/reset_games")
def reset_games():
    os.makedirs("data", exist_ok=True)
    with open("data/games.json", "w", encoding="utf-8") as f:
        json.dump([], f)
    return "已清空所有局的紀錄。"

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
