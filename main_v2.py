from flask import Flask, request, abort
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

if not hasattr(app, 'current_road'):
    app.current_road = []

def build_aux_roads(main_road, offset):
    aux_road = []
    for i in range(offset, len(main_road)):
        if main_road[i] == "和":
            continue
        j = i - offset
        while j >= 0 and main_road[j] == "和":
            j -= 1
        if j < 0:
            continue
        if main_road[i] == main_road[j]:
            aux_road.append("紅")
        else:
            aux_road.append("藍")
    return aux_road

def predict_by_roads(main_road):
    filtered = [r for r in main_road if r != "和"]
    if len(filtered) < 5:
        return "資料太少，看一把"

    big_eye = build_aux_roads(main_road, 2)
    small_road = build_aux_roads(main_road, 3)
    cockroach = build_aux_roads(main_road, 4)

    reds = 0
    blues = 0
    for road in [big_eye, small_road, cockroach]:
        if len(road) > 0:
            if road[-1] == "紅":
                reds += 1
            else:
                blues += 1

    if reds > blues:
        return "推薦: 莊"
    elif blues > reds:
        return "推薦: 閒"
    else:
        return "看一把"

@app.route("/callback", methods=['POST'])
def callback():
    body = request.get_json()
    if body is None:
        abort(400)
    events = body.get("events", [])

    for event in events:
        if event.get("type") == "message" and event["message"]["type"] == "text":
            text = event["message"]["text"].strip().replace(" ", "").replace("-", "")

            # 大量輸入莊閒和
            if all(c in "莊閒和" for c in text) and len(text) >= 5:
                app.current_road = list(text)
                prediction = predict_by_roads(app.current_road)
                reply_message(event["replyToken"], {"type": "text", "text": prediction})
                continue

            # 輸入單一莊閒和
            if text in "莊閒和":
                prediction = predict_by_roads(app.current_road)
                app.current_road.append(text)
                reply_message(event["replyToken"], {"type": "text", "text": prediction})
                continue

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

                prediction = predict_by_roads(app.current_road)
                app.current_road.append(result)
                reply_message(event["replyToken"], {"type": "text", "text": prediction})
                continue

            reply_message(event["replyToken"], {
                "type": "text",
                "text": "請輸入至少5局莊閒和序列，或單局（莊/閒/和），或點數（84）"
            })

    return "OK"

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
