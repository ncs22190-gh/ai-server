import subprocess, os, datetime, requests

VOICEVOX_PATH = r"C:\Program Files\VOICEVOX\VOICEVOX.exe"
MEMORY_DIR = "memory"
voicevox_process = None

def check_system_status():
    return "qwen2.5:3b", "sapi"

def manage_engine(engine_name):
    global voicevox_process
    if engine_name == "voicevox":
        if not voicevox_process:
            voicevox_process = subprocess.Popen([VOICEVOX_PATH])
    elif voicevox_process:
        voicevox_process.terminate()
        voicevox_process = None

def update_memory(user_text, ai_text):
    if not os.path.exists(MEMORY_DIR): os.makedirs(MEMORY_DIR)
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    with open(f"{MEMORY_DIR}/{today}.txt", "a", encoding="utf-8") as f:
        f.write(f"ユーザー: {user_text}\nAI: {ai_text}\n")

def get_history():
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    path = f"{MEMORY_DIR}/{today}.txt"
    return open(path, "r", encoding="utf-8").read() if os.path.exists(path) else ""

def process_command(text):
    if "脳みそリスト" in text: return "選択可能: gemini, qwen2.5:3b"
    return None

def get_character_list():
    try:
        return requests.get("http://localhost:50021/speakers").json()
    except:
        return []

# ここでリストを初期化して保持
CHARACTER_LIST = get_character_list()

def synthesize_voice(text, engine, speaker_id=3):
    if engine == "voicevox":
        try:
            query = requests.post("http://localhost:50021/audio_query", 
                                  params={"speaker": speaker_id, "text": text}).json()
            return requests.post("http://localhost:50021/synthesis", 
                                 params={"speaker": speaker_id}, json=query).content
        except Exception as e:
            print(f"VOICEVOXエラー: {e}")
            return None
    return None