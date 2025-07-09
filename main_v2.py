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

def detect_long_dragon(road):
    count = 1
    last = road[0]
    for outcome in road[1:]:
        if outcome == last:
            count += 1
            if count >= 4:
                return f"長龍: {last}"
        else:
            count = 1
            last = outcome
    return None

def detect_single_jump(road):
    if len(road) < 8:
        return None
    pattern = [road[i] != road[i-1] for i in range(1, len(road))]
    seq = 0
    for p in pattern:
        if p:
            seq += 1
            if seq >= 6:
                return "單跳"
        else:
            seq = 0
    return None

def detect_double_jump(road):
    if len(road) < 8:
        return None
    for i in range(0, len(road)-3, 4):
        if road[i]==road[i+1] and road[i+2]==road[i+3] and road[i]!=road[i+2]:
            continue
        else:
            return None
    return "雙跳"

def detect_one_hall_two_rooms(road):
    if len(road) < 3:
        return None
    last_three = road[-3:]
    if (last_three == ["莊", "閒", "閒"]) or (last_three == ["閒", "莊", "莊"]):
        return "一廳兩房"
    return None

def detect_slope(road):
    # 粗略模擬: 斜坡路會在最後4個交錯增加
    if len(road) < 4:
        return None
    diff_count = sum(1 for i in range(1,4) if road[-i] != road[-i-1])
    if diff_count == 3:
        return "斜坡路"
    return None

def detect_pair_stick(road):
    # 模擬拍拍黐: 連續3次都出現2連莊或2連閒
    if len(road) < 8:
        return None
    pattern = []
    i = 0
    while i < len(road) - 1:
        if road[i] == road[i+1]:
            pattern.append(road[i])
            i += 2
        else:
            i += 1
    if len(pattern) >= 3:
        return "拍拍黐"
    return None

def detect_patterns(road):
    checks = [
        detect_long_dragon(road),
        detect_single_jump(road),
        detect_double_jump(road),
        detect_one_hall_two_rooms(road),
        detect_slope(road),
        detect_pair_stick(road)
    ]
    patterns = [p for p in checks if p]
    return patterns

@app.route("/callback", methods=['POST'])
def callback():
    body = request.get_json()
    if body is None:
        abort(400)
    events = body.get("events", [])

    if not hasattr(app, 'road'):
        app.road = []

    for event in events:
        if event.get("type") == "message" and event["message"]["type"] == "text":
            text = event["message"]["text"].strip().replace(" ", "").replace("-", "")

            # 輸入前五把
            if all(c in "莊閒和" for c in text) and len(text) == 5:
                app.road = list(text)
                reply_message(event["replyToken"], {"type": "text", "text": "已記錄前五把，請輸入下一把點數"})
                continue

            # 點數輸入
            if len(text) == 2 and text.isdigit():
                p = int(text[0])
                b = int(text[1])
                if p > b:
                    result = "閒"
                elif p < b:
                    result = "莊"
                else:
                    result = "和"

                app.road.append(result)
                if len(app.road) > 50:
                    app.road.pop(0)

                # 偵測所有路型
                patterns = detect_patterns(app.road)
                pattern_text = "未偵測到特別路型"
                if patterns:
                    pattern_text = " | ".join(patterns)

                # 給出建議
                recommend = f"推薦跟{app.road[-1]}" if app.road[-1] != "和" else "看一把"

                reply_message(event["replyToken"], {
                    "type": "text",
                    "text": f"{pattern_text}\n{recommend}"
                })
                continue

            reply_message(event["replyToken"], {
                "type": "text",
                "text": "請輸入前五把結果（如: 閒莊閒莊閒）或下一把點數（如:84）"
            })
    return "OK"

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
