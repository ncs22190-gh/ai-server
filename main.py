import subprocess
import requests
import io
import os
import time
import datetime
import winsound
from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# デフォルトを3bにするため、配列の順序を調整しました
# 0: 3b(軽量), 1: 7b(賢い), 2: gemini(クラウド)
MODEL_STAIRS = ["qwen2.5:3b", "qwen2.5:7b", "gemini"]
current_model_index = 0
GEMINI_API_KEY = "YOUR_GEMINI_API_KEY"

# --- メモリー管理機能 ---
def get_memory_file():
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    return f"memory_{today}.txt"

def save_memory(user_message, ai_response):
    filename = get_memory_file()
    with open(filename, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.datetime.now().strftime('%H:%M:%S')}]\n")
        f.write(f"User: {user_message}\nAI: {ai_response}\n---\n")

def load_recent_memory():
    files = sorted([f for f in os.listdir('.') if f.startswith('memory_')], reverse=True)
    recent_memory = "\n【過去の会話の記憶】\n"
    for file in files[:3]:
        with open(file, "r", encoding="utf-8") as f:
            recent_memory += f.read() + "\n"
    return recent_memory

# --- システム設定プロンプト ---
SYSTEM_PROMPT = """
あなたは車載AIアシスタントです。モデルは「3b(軽量)」「7b(賢い)」「gemini(クラウド)」があり、音声はVOICEVOXで話します。
"""

HTML_UI = """
<!DOCTYPE html>
<html lang="ja">
<head><meta charset="UTF-8"><title>車載 AI</title></head>
<body style="background:#121212; color:#fff; text-align:center; padding:20px;">
    <h1>AI アシスタント</h1>
    <div id="output" style="background:#1e1e1e; padding:15px; border-radius:8px; height:200px; overflow-y:auto; border:1px solid #333; text-align:left;">起動中...</div>
    <button id="btn" style="background:#007bff; color:white; padding:15px; width:100%; border-radius:50px;">タップして話す</button>
    <script>
        const btn = document.getElementById('btn');
        const out = document.getElementById('output');
        const rec = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
        rec.lang = 'ja-JP';
        btn.onclick = () => rec.start();
        rec.onresult = (e) => {
            const text = e.results[0][0].transcript;
            fetch('/api/chat', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({message: text}) })
            .then(res => res.json()).then(data => out.innerText = 'AI: ' + data.response);
        };
    </script>
</body>
</html>
"""

# --- 各種機能 ---
def auto_git_sync(mode="start"):
    try:
        subprocess.run(["git", "add", "."], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["git", "commit", "-m", "Auto sync"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if mode == "start":
            subprocess.run(["git", "pull", "--rebase"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(["git", "push"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            subprocess.run(["git", "push"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except: pass

def change_model(user_input):
    global current_model_index
    if any(k in user_input for k in ["ジェミニ", "ジェミナイ"]): current_model_index = 2; return "Geminiモードにします。"
    if any(k in user_input for k in ["軽く", "速く"]): current_model_index = 0; return "3bモデルにします。"
    if any(k in user_input for k in ["賢く", "深く"]): current_model_index = 1; return "7bモデルにします。"
    return None

def chat_with_ollama(prompt):
    try:
        res = requests.post("http://localhost:11434/api/generate", json={"model": MODEL_STAIRS[current_model_index], "prompt": prompt, "stream": False}, timeout=60)
        return res.json().get("response", "エラー")
    except: return "接続失敗"

def speak_voicevox(text):
    try:
        query = requests.post("http://localhost:50021/audio_query", params={"text": text, "speaker": 2}, timeout=5).json()
        synth = requests.post("http://localhost:50021/synthesis", params={"speaker": 2}, json=query, timeout=30)
        with open("temp.wav", "wb") as f: f.write(synth.content)
        winsound.PlaySound("temp.wav", winsound.SND_FILENAME)
    except: pass

def is_voicevox_running():
    try: return "VOICEVOX.exe" in subprocess.check_output(["tasklist"], text=True)
    except: return False

def launch_voicevox():
    path = r"C:\Program Files\VOICEVOX\VOICEVOX.exe"
    if os.path.exists(path):
        subprocess.Popen([path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(5)

def is_ollama_running():
    try: return "ollama" in subprocess.check_output(["tasklist"], text=True).lower()
    except: return False

def launch_ollama():
    subprocess.Popen([os.path.expanduser(r"~\AppData\Local\Programs\Ollama\ollama.exe"), "serve"], shell=True)
    time.sleep(10)

@app.route('/')
def index(): return render_template_string(HTML_UI)

@app.route('/api/chat', methods=['POST'])
def chat_api():
    global current_model_index
    user_message = request.json.get("message", "")
    notice = change_model(user_message)
    if notice:
        speak_voicevox(notice)
        return jsonify({"response": notice, "current_model": MODEL_STAIRS[current_model_index]})
    
    full_prompt = SYSTEM_PROMPT + load_recent_memory() + "\nUser: " + user_message
    ai_response = chat_with_ollama(full_prompt) if MODEL_STAIRS[current_model_index] != "gemini" else "Gemini未設定"
    
    save_memory(user_message, ai_response)
    speak_voicevox(ai_response)
    auto_git_sync(mode="save")
    return jsonify({"response": ai_response, "current_model": MODEL_STAIRS[current_model_index]})

def main():
    auto_git_sync(mode="start")
    if not is_ollama_running(): launch_ollama()
    if not is_voicevox_running(): launch_voicevox()
    app.run(host='0.0.0.0', port=5000, debug=False)

if __name__ == "__main__":
    main()

