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

def build_big_road(history):
    road = []
    col = []
    last = ""
    for result in history:
        if result == last:
            col.append(result)
        else:
            if col:
                road.append(col)
            col = [result]
            last = result
    if col:
        road.append(col)
    return road

def calc_eye_routes(big_road):
    def get_col_len(col):
        return len(col)
    def make_route(start_row):
        route = []
        for col in range(1, len(big_road)):
            left1 = get_col_len(big_road[col-1]) if col-1 < len(big_road) else 0
            left2 = get_col_len(big_road[col-2]) if col-2 < len(big_road) else 0
            if start_row < left1 and start_row < left2:
                route.append("紅" if left1 == left2 else "藍")
        return route
    big_eye = make_route(1)
    small = make_route(2)
    cockroach = make_route(3)
    return big_eye, small, cockroach

def predict_by_routes(current_result, big_eye, small, cockroach):
    reds = sum([big_eye[-1:] == ["紅"], small[-1:] == ["紅"], cockroach[-1:] == ["紅"]])
    blues = sum([big_eye[-1:] == ["藍"], small[-1:] == ["藍"], cockroach[-1:] == ["藍"]])
    if reds > blues:
        return current_result[-1]  # 繼續跟趨勢
    elif blues > reds:
        return "閒" if current_result[-1] == "莊" else "莊"
    else:
        return "看一把"

@app.route("/callback", methods=['POST'])
def callback():
    body = request.get_json()
    if body is None:
        abort(400)
    events = body.get("events", [])
    games = load_games()

    if not hasattr(app, 'current_session'):
        app.current_session = []

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
                big_road = build_big_road(app.current_session)
                big_eye, small, cockroach = calc_eye_routes(big_road)
                suggestion = predict_by_routes(app.current_session, big_eye, small, cockroach)
                reply_message(event["replyToken"], {"type": "text", "text": f"推薦:{suggestion}"})
                continue

            if len(text) == 2 and text.isdigit():
                p, b = int(text[0]), int(text[1])
                if p > b:
                    result = "閒"
                elif p < b:
                    result = "莊"
                else:
                    result = "和"
                app.current_session.append(result)
                if len(app.current_session) > 40:
                    app.current_session.pop(0)
                big_road = build_big_road(app.current_session)
                big_eye, small, cockroach = calc_eye_routes(big_road)
                suggestion = predict_by_routes(app.current_session, big_eye, small, cockroach)
                reply_message(event["replyToken"], {"type": "text", "text": suggestion})
                continue

            reply_message(event["replyToken"], {
                "type": "text",
                "text": "請輸入整局（莊閒和）、前三把（閒莊閒）、或點數（84）"
            })
    return "OK"

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
