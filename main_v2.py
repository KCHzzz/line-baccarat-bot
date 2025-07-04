from flask import Flask, request, abort, send_from_directory
import os
import json
import requests
import matplotlib.pyplot as plt

app = Flask(__name__)

CHANNEL_ACCESS_TOKEN = os.getenv("CHANNEL_ACCESS_TOKEN")
CHANNEL_SECRET = os.getenv("CHANNEL_SECRET")

user_data = {}

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

def draw_road_and_bead(match_results):
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.axis('off')

    # -------------------------------
    # 畫大路 (左邊)
    x_offset = 0
    y_levels = {}
    max_col = 0
    for i, result in enumerate(match_results):
        if i == 0 or result != match_results[i-1]:
            x_offset += 1
            y_levels[x_offset] = 0
        else:
            y_levels[x_offset] += 1
        y = -y_levels[x_offset]
        color = 'red' if result == '莊' else ('blue' if result == '閒' else 'green')
        ax.add_patch(plt.Circle((x_offset, y), 0.4, color=color, ec='black'))
        max_col = max(max_col, x_offset)

    # -------------------------------
    # 畫珠盤路 (右邊)
    for j, result in enumerate(match_results):
        x = max_col + 3 + (j % 6)
        y = -(j // 6)
        color = 'red' if result == '莊' else ('blue' if result == '閒' else 'green')
        ax.add_patch(plt.Circle((x, y), 0.4, color=color, ec='black'))

    # -------------------------------
    ax.set_xlim(0, max_col + 10)
    ax.set_ylim(-max(6, len(match_results) // 6 + 1), 1)
    plt.tight_layout()
    plt.savefig("static/baccarat_result.png")
    plt.close()

@app.route("/callback", methods=['POST'])
def callback():
    body = request.get_json()
    if body is None:
        abort(400)
    events = body.get("events", [])
    for event in events:
        if event.get("type") == "message" and event["message"]["type"] == "text":
            user_id = event["source"]["userId"]
            text = event["message"]["text"].strip()
            clean_text = text.replace(" ", "").replace("-", "").replace("\n", "")

            # 處理前三把
            if len(clean_text) == 3 and all(c in ["莊", "閒", "和"] for c in clean_text):
                user_data[user_id] = {
                    "current_match": list(clean_text)
                }
                reply_message(event["replyToken"], {"type":"text", "text":"已記錄前三把結果，請輸入下一把點數"})
                continue

            # 處理點數
            if len(clean_text) == 2 and clean_text.isdigit():
                if user_id not in user_data or "current_match" not in user_data[user_id]:
                    reply_message(event["replyToken"], {"type":"text", "text":"請先輸入前三把結果（如：莊閒閒）"})
                    continue
                p = int(clean_text[0])
                b = int(clean_text[1])
                if p == b:
                    result = "和"
                elif p > b:
                    result = "閒"
                else:
                    result = "莊"
                user_data[user_id]["current_match"].append(result)
                reply_message(event["replyToken"], {"type":"text", "text":"已記錄"})
                continue

            # 結束後回傳圖片
            if clean_text == "結束":
                if user_id not in user_data or "current_match" not in user_data[user_id]:
                    reply_message(event["replyToken"], {"type":"text", "text":"尚未有對局資料，請先開始一場對局"})
                    continue
                match = user_data[user_id]["current_match"]
                draw_road_and_bead(match)
                img_url = f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}/static/baccarat_result.png"
                reply_message(event["replyToken"], {
                    "type":"image",
                    "originalContentUrl": img_url,
                    "previewImageUrl": img_url
                })
                del user_data[user_id]
                continue

            reply_message(event["replyToken"], {"type":"text", "text":"請輸入前三把結果（如：莊閒閒）、點數（如：46）或輸入 結束"})
    return "OK"

# 靜態檔案路徑
@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory('static', filename)

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
