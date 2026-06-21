import subprocess, time, os, psutil, requests, datetime

VOICEVOX_PATH = r"C:\Program Files\VOICEVOX\VOICEVOX.exe"
MEMORY_DIR = "memory"
SKILLS_DIR = "skills"
voicevox_process = None

def check_system_status():
    # ネット疎通確認
    try:
        requests.get("https://www.google.com", timeout=2)
        net_ok = True
    except: net_ok = False
    
    # 負荷確認
    cpu = psutil.cpu_percent()
    mem = psutil.virtual_memory().percent
    
    if net_ok and cpu < 70 and mem < 80:
        return "gemini", "voicevox"
    return "qwen2.5:3b", "sapi"

def manage_engine(engine_name):
    global voicevox_process
    if engine_name == "voicevox":
        # 既に起動確認のURL（ポート50021）に繋がるなら何もしない
        try:
            requests.get("http://localhost:50021/speakers", timeout=2)
            return
        except:
            if not voicevox_process:
                voicevox_process = subprocess.Popen([VOICEVOX_PATH])
                time.sleep(10)
                
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
    if "脳みそリスト" in text: return "選択可能: gemini, qwen2.5:3b, qwen2.5:7b"
    if "スキル追加" in text:
        # ここにファイル更新ロジックを実装
        return "スキルを更新しました"
    return None