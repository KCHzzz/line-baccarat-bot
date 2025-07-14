# 539.py
# LINE Bot 記錄539開獎號碼，統計尾數，推薦下注
# 在 Render 上自動綁定 0.0.0.0:PORT

from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

from collections import Counter
import os
import csv

app = Flask(__name__)

# 環境變數
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")

# 安全檢查，避免忘記設定
if not LINE_CHANNEL_ACCESS_TOKEN or not LINE_CHANNEL_SECRET:
    raise SystemExit("❌ 環境變數 LINE_CHANNEL_ACCESS_TOKEN 或 LINE_CHANNEL_SECRET 尚未設定，請到 Render > Environment Variables 設定。")

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# 資料庫檔案
DATA_FILE = "results.csv"

# 確保資料檔存在
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w") as f:
        f.write("")

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    text = event.message.text.strip()
    reply = ""

    # 處理輸入 /record 指令
    if text.startswith("/record"):
        try:
            parts = text.replace("/record", "").strip()
            nums = [int(x) for x in parts.split(",")]
            if len(nums) != 5:
                reply = "⚠️ 請輸入五個號碼，例如：/record 12,25,33,8,19"
            else:
                # 寫入 CSV
                with open(DATA_FILE, "a", newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(nums)
                reply = f"✅ 已記錄：{','.join(map(str, nums))}"

                # 分析所有尾數
                tails = []
                with open(DATA_FILE) as f:
                    reader = csv.reader(f)
                    for row in reader:
                        for num in row:
                            tails.append(int(num) % 10)

                counter = Counter(tails)
                top_tail = counter.most_common(1)[0][0]

                reply += "\n📊 熱門尾數：\n"
                for tail, count in counter.most_common():
                    reply += f"{tail} 尾：{count} 次\n"
                reply += f"\n🔥 推薦下期下注：{top_tail} 尾"

        except Exception as e:
            reply = "⚠️ 格式錯誤，請輸入例如：/record 12,25,33,8,19"

    else:
        reply = "請用 /record 12,25,33,8,19 來記錄開獎號碼"

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply)
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
