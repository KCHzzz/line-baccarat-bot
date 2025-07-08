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

# 副路生成
def build_aux_roads(road, offset):
    result = []
    if len(road) < offset + 2:
        return result

    for i in range(offset + 1, len(road)):
        if i - offset - 1 < 0:
            continue
        if road[i] == road[i - offset]:
            result.append("紅")
        else:
            result.append("藍")
    return result

# 根據副路最後 3 格推測
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
        last3 = road[-3:] if len(road) >= 3 else road
        for color in last3:
            if color == "紅":
                reds += 1
            elif color == "藍":
                blues += 1

    if reds > blues:
        return "莊"
    elif blues > reds:
        return "閒"
    else:
        return "看一把"

@app.route("/callback", methods=['POST'])
def callback():
    body = request.get_json()
    if body is None:
        abort(400)
    events = body.get("events", [])

    if not hasattr(app, 'main_road'):
        app.main_road = []

    for event in events:
        if event.get("type") == "message" and event["message"]["type"] == "text":
            text = event["message"]["text"].strip().replace(" ", "").replace("-", "")

            # 輸入前五把
            if all(c in "莊閒和" for c in text) and len(text) == 5:
                app.main_road = list(text)
                prediction = predict_by_roads(app.main_road)
                reply_message(event["replyToken"], {"type": "text", "text": prediction})
                continue

            # 點數輸入
            if len(text) == 2 and text.isdigit():
                p = int(text[0])
                b = int(text[1])
                if p > b:
                    app.main_road.append("閒")
                elif p < b:
                    app.main_road.append("莊")
                else:
                    app.main_road.append("和")

                prediction = predict_by_roads(app.main_road)
                reply_message(event["replyToken"], {"type": "text", "text": prediction})
                continue

            reply_message(event["replyToken"], {
                "type": "text",
                "text": "請輸入前五把結果（例如：閒莊閒莊閒），或點數（例如84）"
            })
    return "OK"

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
