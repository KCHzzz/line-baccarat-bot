from flask import Flask, request, abort
import os
import json
import requests
from collections import Counter

app = Flask(__name__)

CHANNEL_ACCESS_TOKEN = os.getenv("CHANNEL_ACCESS_TOKEN")
CHANNEL_SECRET = os.getenv("CHANNEL_SECRET")

# 你的 GitHub raw json 檔案網址
GITHUB_RAW_URL = "https://raw.githubusercontent.com/KCHzzz/line-baccarat-bot/main/data/games.json"

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

def load_games():
    os.makedirs("data", exist_ok=True)
    file_path = "data/games.json"

    # 如果本地沒檔案，就從 GitHub 拉
    if not os.path.exists(file_path):
        try:
            res = requests.get(GITHUB_RAW_URL)
            if res.status_code == 200:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(res.text)
        except Exception as e:
            print("下載 GitHub games.json 發生錯誤：", e)

    # 讀檔
    if os.path.exists(file_path):
        with open(file_path, encoding="utf-8") as f:
            return json.load(f)
    else:
        return []

def save_games(games):
    with open("data/games.json", "w", encoding="utf-8") as f:
        json.dump(games, f, ensure_ascii=False, indent=2)

def predict_next(last_three, games):
    next_moves = []
    for game in games:
        for i in range(len(game) - 3):
            if game[i:i+3] == last_three:
                next_moves.append(game[i+3])
    if not next_moves:
        return "看一把"
    counts = Counter(next_moves)
    most_common = counts.most_common()
    if len(most_common) > 1 and most_common[0][1] == most_common[1][1]:
        return "看一把"
    else:
        return most_common[0][0]

@app.route("/callback", methods=['POST'])
def callback():
    body = request.get_json()
    if body is None:
        abort(400)
    events = body.get("events", [])
    games = load_games()

    # session: 用來記錄目前對局（尚未結束的）
    if not hasattr(app, 'current_session'):
        app.current_session = []

    for event in events:
        if event.get("type") == "message" and event["message"]["type"] == "text":
            text = event["message"]["text"].strip().replace(" ", "").replace("-", "")

            # 輸入整局（莊閒和）
            if all(c in "莊閒和" for c in text) and len(text) >= 3:
                one_game = list(text)
                games.append(one_game)
                save_games(games)
                summary = f"莊:{one_game.count('莊')} 閒:{one_game.count('閒')} 和:{one_game.count('和')}"
                reply_message(event["replyToken"], {
                    "type": "text",
                    "text": summary
                })
                continue

            # 輸入前三把（例如 閒莊閒）
            if all(c in "莊閒和" for c in text) and len(text) == 3:
                app.current_session = list(text)
                prediction = predict_next(app.current_session, games)
                reply_message(event["replyToken"], {
                    "type": "text",
                    "text": prediction
                })
                continue

            # 輸入點數（例如 84）
            if len(text) == 2 and text.isdigit():
                p = int(text[0])
                b = int(text[1])
                if p > b:
                    result = "閒"
                elif p < b:
                    result = "莊"
                else:
                    result = "和"
                app.current_session.append(result)
                if len(app.current_session) > 3:
                    app.current_session.pop(0)
                prediction = predict_next(app.current_session, games)
                reply_message(event["replyToken"], {
                    "type": "text",
                    "text": prediction
                })
                continue

            # 如果都不是
            reply_message(event["replyToken"], {
                "type": "text",
                "text": "請輸入整局結果（莊閒和），或前三把（閒莊閒），或點數（例如84）"
            })
    return "OK"

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
