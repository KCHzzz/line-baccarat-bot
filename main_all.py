
from flask import Flask, request, abort
import os
import json
import requests
from collections import Counter

app = Flask(__name__)

CHANNEL_ACCESS_TOKEN = os.getenv("CHANNEL_ACCESS_TOKEN")
CHANNEL_SECRET = os.getenv("CHANNEL_SECRET")

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
    if not os.path.exists(file_path):
        try:
            res = requests.get(GITHUB_RAW_URL)
            if res.status_code == 200:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(res.text)
        except Exception as e:
            print("下載 GitHub games.json 發生錯誤：", e)
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

    if not hasattr(app, 'current_session'):
        app.current_session = []
    if not hasattr(app, 'predicted_next'):
        app.predicted_next = None
    if not hasattr(app, 'first_predict_done'):
        app.first_predict_done = False

    for event in events:
        if event.get("type") == "message" and event["message"]["type"] == "text":
            text = event["message"]["text"].strip().replace(" ", "").replace("-", "")

            if all(c in "莊閒和" for c in text) and len(text) > 3:
                one_game = list(text)
                games.append(one_game)
                save_games(games)
                summary = f"莊:{one_game.count('莊')} 閒:{one_game.count('閒')} 和:{one_game.count('和')}"
                reply_message(event["replyToken"], {"type": "text", "text": summary})
                continue

            if all(c in "莊閒和" for c in text) and len(text) == 3:
                app.current_session = list(text)
                app.predicted_next = predict_next(app.current_session, games)
                app.first_predict_done = False
                reply_message(event["replyToken"], {"type": "text", "text": f"推薦:{app.predicted_next}"})
                app.first_predict_done = True
                continue

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
                if len(app.current_session) > 4:
                    app.current_session.pop(0)

                if len(app.current_session) == 4:
                    games.append(app.current_session.copy())
                    save_games(games)

                if app.first_predict_done:
                    reply_message(event["replyToken"], {"type": "text", "text": result})
                else:
                    reply_message(event["replyToken"], {"type": "text", "text": f"推薦:{result}"})
                    app.first_predict_done = True

                app.predicted_next = predict_next(app.current_session[-3:], games)
                continue

            reply_message(event["replyToken"], {
                "type": "text",
                "text": "請輸入整局（莊閒和）、前三把（閒莊閒）、或點數（84）"
            })
    return "OK"

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
