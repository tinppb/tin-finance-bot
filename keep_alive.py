from flask import Flask
from threading import Thread

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot quản lý tài chính đang hoạt động ổn định 24/7 trên Render!"

def run():
    # Render yêu cầu chạy ở port 10000
    app.run(host='0.0.0.0', port=10000)

def keep_alive():
    t = Thread(target=run)
    t.start()