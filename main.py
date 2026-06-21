import subprocess, requests, os, time, datetime, winsound
from flask import Flask, request, jsonify
from flask_cors import CORS
from gtts import gTTS
import google.generativeai as genai

app = Flask(__name__)
CORS(app)

# APIキー設定（Windows環境変数から取得）
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

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
    os.makedirs(os.path.dirname(filename) if os.path.dirname(filename) else ".", exist_ok=True)
    with open(filename, "w", encoding="utf-8") as f: f.write(content)
    auto_git_sync(mode="save")
    return f"{filename} を更新しました。"

# --- スキル・ルール・モデル管理 ---
def load_knowledge():
    return open("rule_flow.txt", "r", encoding="utf-8").read() if os.path.exists("rule_flow.txt") else ""

def list_skills():
    if not os.path.exists("skills"): return "スキルフォルダがありません。"
    return "現在保持しているスキル: " + ", ".join([f.replace("_skill.txt", "") for f in os.listdir("skills")])

def get_skill_content(user_input):
    skills_dir = "skills"
    if not os.path.exists(skills_dir): return ""
    for f in os.listdir(skills_dir):
        skill_name = f.replace("_skill.txt", "")
        if skill_name in user_input:
            return f"\n【{skill_name}スキル】\n" + open(os.path.join(skills_dir, f), "r", encoding="utf-8").read()
    return ""

# --- 音声エンジン管理 ---
def is_voicevox_running():
    try: return "VOICEVOX.exe" in subprocess.check_output(["tasklist"], text=True)
    except: return False

def launch_voicevox():
    path = r"C:\Program Files\VOICEVOX\VOICEVOX.exe"
    if os.path.exists(path):
        subprocess.Popen([path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(10)

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

# --- AI本体 (脳みそ) ---
def chat_with_ollama(prompt):
    model_name = MODEL_STAIRS[current_model_index]
    if model_name == "gemini":
        try:
            model = genai.GenerativeModel('gemini-1.5-flash')
            return model.generate_content(prompt).text
        except Exception as e: return f"Geminiエラー: {str(e)}"
    
    url = "http://localhost:11434/api/generate"
    payload = {"model": model_name, "prompt": prompt, "stream": False}
    try:
        res = requests.post(url, json=payload, timeout=60)
        return res.json().get("response", "エラー")
    except: return "接続失敗"

# --- メインロジック ---
@app.route('/api/chat', methods=['POST'])
def chat_api():
    user_message = request.json.get("message", "")
    global current_engine, current_model_index
    
    # 1. 管理コマンド (スキル・ルール・モデル)
    if "スキル何ある" in user_message: return jsonify({"response": list_skills()})
    if "スキル作成：" in user_message:
        parts = user_message.split("：")
        return jsonify({"response": update_file(f"skills/{parts[1]}_skill.txt", parts[2])})
    if "モデル何ある" in user_message: return jsonify({"response": "利用可能なモデル: " + ", ".join(MODEL_STAIRS)})
    for i, model in enumerate(MODEL_STAIRS):
        if f"{model}にして" in user_message:
            current_model_index = i
            return jsonify({"response": f"脳みそを {model} に切り替えました。"})
    if "ルール" in user_message and "更新" in user_message:
        return jsonify({"response": update_file("rule_flow.txt", user_message.split("更新：")[-1])})

    # 2. エンジン切替
    if "ローカル音声" in user_message:
        if is_voicevox_running(): subprocess.run(["taskkill", "/f", "/im", "VOICEVOX.exe"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        current_engine = "local"; return jsonify({"response": "ローカル音声にしました。"})
    if "クラウド音声" in user_message:
        current_engine = "google"; return jsonify({"response": "クラウド音声にしました。"})
    if "VOICEVOX" in user_message:
        if not is_voicevox_running(): launch_voicevox()
        current_engine = "voicevox"; return jsonify({"response": "VOICEVOXにしました。"})

    # 3. 応答生成
    prompt = f"【基本ルール】\n{load_knowledge()}\n{get_skill_content(user_message)}\nUser: {user_message}"
    ai_response = chat_with_ollama(prompt)
    
    speak(ai_response)
    auto_git_sync(mode="save")
    return jsonify({"response": ai_response})

if __name__ == "__main__":
    auto_git_sync(mode="start")
    app.run(host='0.0.0.0', port=5000)

