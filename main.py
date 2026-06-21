import subprocess
import requests
import os
import time
import datetime
import winsound
from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# --- 設定 ---
MODEL_STAIRS = ["qwen2.5:3b", "qwen2.5:7b", "gemini"]
current_model_index = 0
current_engine = "voicevox"
current_speaker_id = 2
# 必要に応じて環境変数から取得するように変更も可能です
GEMINI_API_KEY = "YOUR_GEMINI_API_KEY"

# --- 外部記憶・Git ---
def auto_git_sync(mode="start"):
    try:
        subprocess.run(["git", "add", "."], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["git", "commit", "-m", "Auto sync"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if mode == "start":
            subprocess.run(["git", "pull", "--rebase"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(["git", "push"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            subprocess.run(["git", "push"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass

def get_memory_file():
    return f"memory_{datetime.datetime.now().strftime('%Y-%m-%d')}.txt"

def save_memory(user_message, ai_response):
    with open(get_memory_file(), "a", encoding="utf-8") as f:
        f.write(f"[{datetime.datetime.now().strftime('%H:%M:%S')}]\nUser: {user_message}\nAI: {ai_response}\n---\n")

def load_recent_memory():
    files = sorted([f for f in os.listdir('.') if f.startswith('memory_')], reverse=True)
    recent_memory = "\n【過去の会話の記憶】\n"
    for file in files[:3]:
        with open(file, "r", encoding="utf-8") as f:
            recent_memory += f.read() + "\n"
    return recent_memory

# --- VOICEVOX管理 ---
def is_voicevox_running():
    try:
        output = subprocess.check_output(["tasklist"], text=True)
        return "VOICEVOX.exe" in output
    except Exception:
        return False

def launch_voicevox():
    path = r"C:\Program Files\VOICEVOX\VOICEVOX.exe"
    if os.path.exists(path):
        subprocess.Popen([path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(10)

def get_voicevox_characters():
    try:
        res = requests.get("http://localhost:50021/speakers", timeout=5)
        return {s["name"]: s["styles"][0]["id"] for s in res.json()}
    except Exception:
        return {"ずんだもん": 2}

# --- 音声再生 ---
def speak(text):
    global current_engine
    if current_engine == "voicevox":
        try:
            query = requests.post("http://localhost:50021/audio_query", params={"text": text, "speaker": current_speaker_id}, timeout=5).json()
            synth = requests.post("http://localhost:50021/synthesis", params={"speaker": current_speaker_id}, json=query, timeout=30)
            with open("temp.wav", "wb") as f: f.write(synth.content)
            winsound.PlaySound("temp.wav", winsound.SND_FILENAME)
        except Exception:
            pass
    else:
        try:
            import win32com.client
            win32com.client.Dispatch("SAPI.SpVoice").Speak(text)
        except Exception:
            pass

# --- AI本体 ---
def chat_with_ollama(prompt):
    url = "http://localhost:11434/api/generate"
    payload = {"model": MODEL_STAIRS[current_model_index], "prompt": prompt, "stream": False}
    try:
        res = requests.post(url, json=payload, timeout=60)
        return res.json().get("response", "エラー")
    except Exception:
        return "接続失敗"

# --- 設定切替 ---
def change_setting(user_input):
    global current_model_index, current_engine, current_speaker_id
    
    if "ジェミニ" in user_input: current_model_index = 2; return "Geminiモードにしました。"
    if "軽く" in user_input: current_model_index = 0; return "3bモデルにしました。"
    
    if "ローカル" in user_input:
        if is_voicevox_running():
            subprocess.run(["taskkill", "/f", "/im", "VOICEVOX.exe"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        current_engine = "local"
        return "ローカル音声に切り替えました。"
    
    chars = get_voicevox_characters()
    for name, sid in chars.items():
        if name in user_input:
            if not is_voicevox_running(): launch_voicevox()
            current_engine = "voicevox"
            current_speaker_id = sid
            return f"{name}に変更しました。"
    return None

@app.route('/api/chat', methods=['POST'])
def chat_api():
    user_message = request.json.get("message", "")
    notice = change_setting(user_message)
    if notice:
        speak(notice)
        return jsonify({"response": notice})
    
    full_prompt = load_recent_memory() + "\nUser: " + user_message
    ai_response = chat_with_ollama(full_prompt)
    
    save_memory(user_message, ai_response)
    speak(ai_response)
    auto_git_sync(mode="save")
    return jsonify({"response": ai_response})

if __name__ == "__main__":
    auto_git_sync(mode="start")
    app.run(host='0.0.0.0', port=5000)
