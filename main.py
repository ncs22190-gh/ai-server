import subprocess
import requests
import os
import time
import datetime
import winsound
from flask import Flask, request, jsonify
from flask_cors import CORS
from gtts import gTTS

app = Flask(__name__)
CORS(app)

# --- 設定 ---
MODEL_STAIRS = ["qwen2.5:3b", "qwen2.5:7b", "gemini"]
current_model_index = 0
current_engine = "voicevox"
current_speaker_id = 2

# --- 外部記憶・Git・ファイル操作 ---
def auto_git_sync(mode="start"):
    try:
        subprocess.run(["git", "add", "."], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["git", "commit", "-m", "Auto sync"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if mode == "start":
            subprocess.run(["git", "pull", "--rebase"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["git", "push"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception: pass

def update_file(filename, content):
    with open(filename, "w", encoding="utf-8") as f: f.write(content)
    auto_git_sync(mode="save")
    return f"{filename} を更新しました。"

def save_memory(user_message, ai_response):
    filename = f"memory_{datetime.datetime.now().strftime('%Y-%m-%d')}.txt"
    with open(filename, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.datetime.now().strftime('%H:%M:%S')}]\nUser: {user_message}\nAI: {ai_response}\n---\n")

def load_knowledge():
    return open("rule_flow.txt", "r", encoding="utf-8").read() if os.path.exists("rule_flow.txt") else ""

def get_skill_content(user_input):
    skills_dir = "skills"
    if not os.path.exists(skills_dir): return ""
    if "DIY" in user_input and os.path.exists(os.path.join(skills_dir, "diy_skill.txt")):
        return "\n【DIYスキル】\n" + open(os.path.join(skills_dir, "diy_skill.txt"), "r", encoding="utf-8").read()
    return ""

# --- VOICEVOX管理 ---
def is_voicevox_running():
    try: return "VOICEVOX.exe" in subprocess.check_output(["tasklist"], text=True)
    except: return False

def launch_voicevox():
    path = r"C:\Program Files\VOICEVOX\VOICEVOX.exe"
    if os.path.exists(path):
        subprocess.Popen([path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(10)

# --- 音声再生 ---
def speak(text):
    global current_engine
    if current_engine == "voicevox":
        try:
            query = requests.post("http://localhost:50021/audio_query", params={"text": text, "speaker": current_speaker_id}, timeout=5).json()
            synth = requests.post("http://localhost:50021/synthesis", params={"speaker": current_speaker_id}, json=query, timeout=30)
            with open("temp.wav", "wb") as f: f.write(synth.content)
            winsound.PlaySound("temp.wav", winsound.SND_FILENAME)
        except: pass
    elif current_engine == "google":
        try:
            tts = gTTS(text=text, lang='ja')
            tts.save("temp.mp3")
            os.startfile("temp.mp3")
        except: pass
    else:
        try:
            import win32com.client
            win32com.client.Dispatch("SAPI.SpVoice").Speak(text)
        except: pass

# --- AI本体 ---
def chat_with_ollama(prompt):
    url = "http://localhost:11434/api/generate"
    payload = {"model": MODEL_STAIRS[current_model_index], "prompt": prompt, "stream": False}
    try:
        res = requests.post(url, json=payload, timeout=60)
        return res.json().get("response", "エラー")
    except: return "接続失敗"

# --- メインロジック ---
@app.route('/api/chat', methods=['POST'])
def chat_api():
    user_message = request.json.get("message", "")
    global current_engine
    
    # 1. ルール更新
    if "ルール" in user_message and "更新" in user_message:
        return jsonify({"response": update_file("rule_flow.txt", user_message.split("更新：")[-1])})

    # 2. エンジン切り替え
    if "ローカル音声" in user_message:
        if is_voicevox_running(): subprocess.run(["taskkill", "/f", "/im", "VOICEVOX.exe"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        current_engine = "local"; return jsonify({"response": "ローカル音声に切り替えました。"})
    if "クラウド音声" in user_message:
        current_engine = "google"; return jsonify({"response": "クラウド音声(Google)に切り替えました。"})
    if "VOICEVOX" in user_message:
        if not is_voicevox_running(): launch_voicevox()
        current_engine = "voicevox"; return jsonify({"response": "VOICEVOXに切り替えました。"})
    
    # 3. 生成
    prompt = f"【基本ルール】\n{load_knowledge()}\n{get_skill_content(user_message)}\nUser: {user_message}"
    ai_response = chat_with_ollama(prompt)
    
    save_memory(user_message, ai_response)
    speak(ai_response)
    auto_git_sync(mode="save")
    return jsonify({"response": ai_response})

if __name__ == "__main__":
    auto_git_sync(mode="start")
    app.run(host='0.0.0.0', port=5000)