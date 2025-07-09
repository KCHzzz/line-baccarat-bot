from flask import Flask, request, abort
import os
import json
import requests
from collections import Counter

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

# 分析牌路
def analyze_road_pattern(history):
    tips = []

    # 1. 長莊、長閑
    if len(history) >= 4:
        if all(h == '莊' for h in history[-4:]):
            tips.append("長莊")
        if all(h == '閒' for h in history[-4:]):
            tips.append("長閒")

    # 2. 單跳
    if len(history) >= 8:
        single_jump = True
        for i in range(-8, -1):
            if history[i] == history[i+1]:
                single_jump = False
                break
        if single_jump:
            tips.append("大路單跳")

    # 3. 雙跳
    if len(history) >= 8:
        double_jump = True
        for i in range(-8, -1, 2):
            if history[i] != history[i+1]:
                double_jump = False
                break
        if double_jump:
            tips.append("大路雙跳")

    # 4. 逢莊跳
    if len(history) >= 7:
        found = 0
        for i in range(-7, -1):
            if history[i] == "莊" and i+1 < 0 and history[i+1] == "閒":
                found +=1
            elif history[i] == "莊":
                found = 0
        if found >=3:
            tips.append("逢莊跳")

    # 5. 逢閒跳
    if len(history) >= 7:
        found = 0
        for i in range(-7, -1):
            if history[i] == "閒" and i+1 < 0 and history[i+1] == "莊":
                found +=1
            elif history[i] == "閒":
                found = 0
        if found >=3:
            tips.append("逢閒跳")

    # 6. 一廳兩房（莊）
    if len(history) >= 6:
        count = 0
        for i in range(-6, -2):
            if history[i:i+3] == ['莊', '閒', '閒']:
                count += 1
        if count >= 2:
            tips.append("一廳兩房(莊)")

    # 7. 一廳兩房（閒）
    if len(history) >= 6:
        count = 0
        for i in range(-6, -2):
            if history[i:i+3] == ['閒', '莊', '莊']:
                count += 1
        if count >= 2:
            tips.append("一廳兩房(閒)")

    # 8. 逢莊連
    if len(history) >= 6:
        col1 = [history[i] for i in range(-6, -5)]
        col2 = [history[i] for i in range(-5, -4)]
        if col1.count('莊') >=2 and col2.count('莊')>=2:
            tips.append("逢莊連")

    # 9. 逢閒連
    if len(history) >= 6:
        col1 = [history[i] for i in range(-6, -5)]
        col2 = [history[i] for i in range(-5, -4)]
        if col1.count('閒') >=2 and col2.count('閒')>=2:
            tips.append("逢閒連")

    # 10. 拍拍黐
    if len(history) >= 6:
        mid_three = history[-6:-3]
        if mid_three.count('莊') >=2 or mid_three.count('閒') >=2:
            tips.append("拍拍黐")

    return tips if tips else ["暫無特別路型"]

@app.route("/callback", methods=['POST'])
def callback():
    body = request.get_json()
    if body is None:
        abort(400)
    events = body.get("events", [])

    if not hasattr(app, 'current_history'):
        app.current_history = []

    for event in events:
        if event.get("type") == "message" and event["message"]["type"] == "text":
            text = event["message"]["text"].strip().replace(" ", "").replace("-", "")

            # 初始化前五局
            if all(c in "莊閒和" for c in text) and len(text) == 5:
                app.current_history = list(text)
                patterns = analyze_road_pattern(app.current_history)
                reply_message(event["replyToken"], {"type": "text", "text": f"已記錄前五把: {''.join(app.current_history)}\n{', '.join(patterns)}"})
                continue

            # 點數輸入
            if len(text) == 2 and text.isdigit():
                p, b = int(text[0]), int(text[1])
                if p > b:
                    result = "閒"
                elif p < b:
                    result = "莊"
                else:
                    result = "和"

                app.current_history.append(result)
                if len(app.current_history) > 30:
                    app.current_history.pop(0)

                patterns = analyze_road_pattern(app.current_history)
                reply_message(event["replyToken"], {"type": "text", "text": f"{result}\n{', '.join(patterns)}"})
                continue

            reply_message(event["replyToken"], {"type": "text", "text": "請輸入五局(莊閒和)或點數(84)"})
    return "OK"

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
