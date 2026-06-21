import socketio, psutil, requests, time, os
from flask import Flask, render_template_string
from flask_socketio import SocketIO, emit
from utils import check_system_status, manage_engine, update_memory, get_history, process_command, synthesize_voice
from prompts import get_system_prompt
from google import genai
from utils import CHARACTER_LIST, synthesize_voice # synthesize_voice をインポート
current_speaker_id = 3 # デフォルトはずんだもん

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

current_model, current_engine = check_system_status()
manage_engine(current_engine)

@socketio.on('voice_input')
def handle_voice(data):
    user_text = data['text']
    mode = data.get('mode', 'live')
    # global 宣言に current_speaker_id を追加
    global current_model, current_engine, current_speaker_id
    
    # 1. コマンド処理
    res = ""
    if "現在の" in user_text or "今の" in user_text:
        res = f"現在はモデルが {current_model}、音声エンジンが {current_engine} です。"
    elif "エンジンを" in user_text:
        if "ボイスボックス" in user_text or "voicevox" in user_text:
            current_engine = "voicevox"
            manage_engine("voicevox")
            res = "音声エンジンをボイスボックスに変更しました。"
        elif "サピ" in user_text or "sapi" in user_text:
            current_engine = "sapi"
            manage_engine("sapi")
            res = "音声エンジンを標準のサピに変更しました。"
    elif "モードを" in user_text:
        if "ジェミニ" in user_text:
            current_model = "gemini"
            res = "脳みそをGeminiに変更しました。"
        elif "ローカル" in user_text:
            current_model = "qwen2.5:3b"
            res = "脳みそをローカルモデルに変更しました。"

    # handle_voice内のコマンド分岐に以下を追加してください
    elif "に変えて" in user_text:
        for char in CHARACTER_LIST:
            if char['name'] in user_text:
                current_speaker_id = char['styles'][0]['id']
                res = f"音声キャラクターを {char['name']} に変更しました。"
                break

    # 2. 通常対話処理（コマンドがない場合）
    if not res:
        prompt = get_system_prompt(user_text, get_history())
        try:
            if current_model == "gemini":
                api_key = os.environ.get("GEMINI_API_KEY")
                client = genai.Client(api_key=api_key)
                res = client.models.generate_content(model='gemini-2.0-flash', contents=prompt).text
            else:
                r = requests.post("http://localhost:11434/api/generate", json={"model": current_model, "prompt": prompt, "stream": False})
                res = r.json().get("response", "応答なし")
        except Exception as e:
            res = f"エラー: {str(e)[:15]}"
        update_memory(user_text, res)

    # 3. 音声合成と応答送信
    audio_data = synthesize_voice(res, current_engine, current_speaker_id)
    emit('ai_response', {
        'user_text': user_text,
        'ai_text': res,
        'ai_audio': audio_data.hex() if audio_data else ""
    })

@app.route('/')
def index():
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <body>
        <h2>AI 対話システム</h2>
        <div>
            <input type="radio" name="mode" value="live" checked> ライブ
            <input type="radio" name="mode" value="chat"> 一問一答
            <button onclick="start()">会話開始</button>
        </div>
        <div id="log" style="height:300px; border:1px solid #ccc; overflow-y:scroll; margin-top:10px;"></div>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
        <script>
            const socket = io();
            const log = document.getElementById('log');
            
            function start() {
                const mode = document.querySelector('input[name="mode"]:checked').value;
                const rec = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
                rec.lang = 'ja-JP';
                rec.continuous = (mode === 'live');
                rec.onresult = (e) => {
                    const text = e.results[e.results.length-1][0].transcript;
                    log.innerHTML += '<p>あなた: ' + text + '</p>';
                    socket.emit('voice_input', {text: text, mode: mode});
                };
                rec.start();
            }
            socket.on('ai_response', (d) => {
                // あなたの発言とAIの回答をそれぞれ表示
                log.innerHTML += '<p><strong>あなた:</strong> ' + d.user_text + '</p>';
                log.innerHTML += '<p><strong>AI:</strong> ' + d.ai_text + '</p>';
                
                // 音声データがあれば再生
                if (d.ai_audio) {
                    const bytes = new Uint8Array(d.ai_audio.match(/.{1,2}/g).map(byte => parseInt(byte, 16)));
                    const blob = new Blob([bytes], {type: 'audio/wav'});
                    const url = URL.createObjectURL(blob);
                    new Audio(url).play();
                }
            });
        </script>
    </body>
    </html>
    """)

if __name__ == "__main__":
    socketio.run(app, host='0.0.0.0', port=5000, debug=False)