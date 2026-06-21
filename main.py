import subprocess, os, time, datetime, winsound
from flask import Flask, render_template_string
from flask_socketio import SocketIO, emit
from gtts import gTTS
from google import genai

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins="*")

# クライアント初期化
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

# --- HTML/JS (ライブ会話・一問一答切り替え) ---
HTML_INTERFACE = """
<!DOCTYPE html>
<html>
<body>
    <h2>AI 対話モード</h2>
    <button onclick="setMode('manual')">一問一答モード</button>
    <button onclick="setMode('live')">ライブ会話モード</button>
    <p>現在のモード: <span id="mode">未選択</span></p>
    <script>
        let mode = 'manual';
        function setMode(m) { mode = m; document.getElementById('mode').innerText = m; }
        // ここにマイク入力とWebSocket通信のロジックを実装
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_INTERFACE)

# --- AI本体 ---
def get_ai_response(prompt):
    try:
        response = client.models.generate_content(model='gemini-2.0-flash', contents=prompt)
        return response.text
    except Exception as e: return f"Geminiエラー: {str(e)}"

# --- WebSocket通信 ---
@socketio.on('voice_input')
def handle_voice(data):
    # 音声認識(文字起こし)後、AI回答生成
    text = data['text']
    response = get_ai_response(text)
    # 応答をスマホ側へ送り返す
    emit('ai_response', {'text': response})

if __name__ == "__main__":
    socketio.run(app, host='0.0.0.0', port=5000)

