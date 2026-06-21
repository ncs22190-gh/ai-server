import socketio, psutil, requests, time, os
from flask import Flask, render_template_string
from flask_socketio import SocketIO, emit
from utils import check_system_status, manage_engine, update_memory, get_history, process_command
from prompts import get_system_prompt
from google import genai

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# 起動時に1回だけ状態判定
current_model, current_engine = check_system_status()
manage_engine(current_engine)

@socketio.on('voice_input')
def handle_voice(data):
    user_text = data['text']
    cmd_res = process_command(user_text)
    if cmd_res:
        emit('ai_response', {'text': cmd_res})
        return
    
    prompt = get_system_prompt(user_text, get_history())
    try:
        if current_model == "gemini":
            client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
            response = client.models.generate_content(model='gemini-2.0-flash', contents=prompt).text
        else:
            response = requests.post("http://localhost:11434/api/generate", json={"model": current_model, "prompt": prompt}).json().get("response")
    except:
        response = "ローカルモデルに切り替えて応答します。"
    
    update_memory(user_text, response)
    emit('ai_response', {'text': response})

@app.route('/')
def index():
    return render_template_string("""
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
    <div id="log" style="height:300px; border:1px solid #ccc; overflow-y:scroll;"></div>
    <button onclick="start()">ライブ開始</button>
    <script>
        const socket = io();
        function start() {
            const rec = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
            rec.continuous = true;
            rec.interimResults = false;
            rec.onresult = (e) => {
                const text = e.results[e.results.length-1][0].transcript;
                socket.emit('voice_input', {text: text});
            };
            rec.start();
        }
        socket.on('ai_response', (d) => {
            const u = new SpeechSynthesisUtterance(d.text);
            window.speechSynthesis.speak(u);
        });
    </script>
    """)

if __name__ == "__main__":
    socketio.run(app, host='0.0.0.0', port=5000, debug=False)