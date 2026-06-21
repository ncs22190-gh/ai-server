import socketio, psutil, requests, time
from flask import Flask, render_template_string
from flask_socketio import SocketIO, emit
from utils import check_system_status, manage_engine, update_memory, get_history, process_command
from prompts import get_system_prompt
from google import genai
import os

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# 初期状態の自動選択
current_model, current_engine = check_system_status()
manage_engine(current_engine)

@socketio.on('voice_input')
def handle_voice(data):
    user_text = data['text']
    # コマンド処理（設定変更・リスト確認）
    cmd_res = process_command(user_text)
    if cmd_res:
        emit('ai_response', {'text': cmd_res})
        return

    # プロンプト構築（履歴・スキル・ルールを統合）
    prompt = get_system_prompt(user_text, get_history())
    
    # AI応答生成（ネット状況に応じた自動切替対応）
    try:
        if current_model == "gemini":
            client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
            response = client.models.generate_content(model='gemini-2.0-flash', contents=prompt).text
        else:
            response = requests.post("http://localhost:11434/api/generate", json={"model": current_model, "prompt": prompt}).json().get("response")
    except:
        response = "ネット接続を確認できないため、ローカルモードで応答します。"

    update_memory(user_text, response)
    emit('ai_response', {'text': response})

@app.route('/')
def index():
    return render_template_string("""
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
    <button onclick="start()">開始</button>
    <script>
        const socket = io();
        function start() {
            const rec = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
            rec.onresult = (e) => socket.emit('voice_input', {text: e.results[0][0].transcript});
            rec.start();
        }
        socket.on('ai_response', (d) => { console.log(d.text); });
    </script>
    """)

if __name__ == "__main__":
    socketio.run(app, host='0.0.0.0', port=5000, debug=False)

