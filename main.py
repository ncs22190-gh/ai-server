import subprocess
import requests
import io
from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
from playsound import playsound

app = Flask(__name__)
CORS(app)

MODEL_STAIRS = ["qwen2.5:7b", "qwen2.5:3b", "gemini"]
current_model_index = 0
GEMINI_API_KEY = "YOUR_GEMINI_API_KEY"

HTML_UI = """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>車載 AI アシスタント</title>
    <style>
        body { font-family: sans-serif; background: #121212; color: #e0e0e0; margin: 0; padding: 20px; display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100vh; }
        .container { text-align: center; width: 100%; max-width: 400px; }
        h1 { font-size: 1.5rem; margin-bottom: 10px; }
        #status { color: #888; margin-bottom: 20px; font-size: 0.9rem; }
        #output { background: #1e1e1e; padding: 15px; border-radius: 8px; min-height: 100px; margin-bottom: 20px; text-align: left; border: 1px solid #333; overflow-y: auto; max-height: 200px; }
        button { background: #007bff; color: white; border: none; padding: 15px 30px; font-size: 1.1rem; border-radius: 50px; cursor: pointer; width: 100%; box-shadow: 0 4px 6px rgba(0,0,0,0.3); transition: background 0.2s; }
        button:active { background: #0056b3; }
    </style>
</head>
<body>
    <div class="container">
        <h1 id="model-display">AI アシスタント</h1>
        <div id="status">接続完了</div>
        <div id="output">ここにAIの応答が表示されます。</div>
        <button id="talk-btn">タップして話す</button>
    </div>

    <script>
        const talkBtn = document.getElementById('talk-btn');
        const outputDiv = document.getElementById('output');
        const modelDisplay = document.getElementById('model-display');
        
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRecognition) {
            alert('お使いのブラウザは音声認識に対応していません。');
        } else {
            const recognition = new SpeechRecognition();
            recognition.lang = 'ja-JP';
            recognition.interimResults = false;

            talkBtn.addEventListener('click', () => {
                recognition.start();
                talkBtn.innerText = '聴取中...';
                talkBtn.style.background = '#dc3545';
            });

            recognition.addEventListener('result', (e) => {
                const text = e.results[0][0].transcript;
                outputDiv.innerText = 'あなた: ' + text;
                sendToAI(text);
            });

            recognition.addEventListener('end', () => {
                talkBtn.innerText = 'タップして話す';
                talkBtn.style.background = '#007bff';
            });
        }

        function sendToAI(text) {
            fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: text })
            })
            .then(res => res.json())
            .then(data => {
                outputDiv.innerText = 'AI: ' + data.response;
                modelDisplay.innerText = 'AI: ' + data.current_model;
            })
            .catch(err => {
                outputDiv.innerText = '通信エラーが発生しました。';
            });
        }
    </script>
</body>
</html>
"""

def auto_git_sync(mode="start"):
    try:
        subprocess.run(["git", "add", "."], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["git", "commit", "-m", "Auto sync by AI Assistant"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        if mode == "start":
            subprocess.run(["git", "pull", "--rebase"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(["git", "push"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        elif mode == "save":
            subprocess.run(["git", "push"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except (subprocess.CalledProcessError, Exception):
        pass

def change_model(user_input):
    global current_model_index
    gemini_keywords = ["ジェジェ", "じぇじぇ", "ジェミニ", "じぇみに", "クラウド"]
    light_keywords = ["遅い", "おそい", "遅く", "重い", "おもい", "軽く", "かるく", "速く", "はやく", "1段階"]
    heavy_keywords = ["賢く", "かしこく", "戻して", "もどして", "深く", "ふかく", "ローカル"]
    
    if any(k in user_input for k in gemini_keywords):
        current_model_index = 2
        return "頭脳を外部クラウドのGeminiモードに切り替えます。"
    if any(k in user_input for k in light_keywords):
        if current_model_index == 0:
            current_model_index = 1
            return f"レスポンス重視で軽量な {MODEL_STAIRS[current_model_index]} に切り替えます。"
    elif any(k in user_input for k in heavy_keywords):
        if current_model_index == 1 or current_model_index == 2:
            current_model_index = 0
            return f"思考力重視のローカルAI {MODEL_STAIRS[current_model_index]} に切り替えます。"
    return None

def chat_with_ollama(prompt):
    url = "http://localhost:11434/api/generate"
    # modelパラメータが正しいか、Ollamaが動いているかを確認するログを追加
    payload = {"model": MODEL_STAIRS[current_model_index], "prompt": prompt, "stream": False}
    try:
        response = requests.post(url, json=payload, timeout=60) # タイムアウトを少し延長
        if response.status_code == 200:
            return response.json().get("response", "エラーが発生しました。")
        else:
            return f"Ollamaエラー: {response.status_code}"
    except Exception as e:
        return f"Ollama接続失敗: {str(e)}"

def chat_with_gemini(prompt):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    try:
        response = requests.post(url, json=payload, timeout=30)
        if response.status_code == 200:
            return response.json()["candidates"][0]["content"]["parts"][0]["text"]
    except requests.exceptions.RequestException:
        return "Gemini APIとの通信に失敗しました。ネット環境を確認してください。"
    return "Geminiから応答を取得できませんでした。"

import os
import requests
import winsound # playsoundの代わりにwinsoundをインポート

def speak_voicevox(text, speaker_id=2):
    base_url = "http://localhost:50021"
    try:
        query_res = requests.post(f"{base_url}/audio_query", params={"text": text, "speaker": speaker_id}, timeout=10)
        if query_res.status_code != 200: return
        
        synth_res = requests.post(f"{base_url}/synthesis", params={"speaker": speaker_id}, json=query_res.json(), timeout=30)
        if synth_res.status_code != 200: return
        
        # WAVをバイナリとして保存
        wav_path = os.path.join(os.getcwd(), "temp.wav")
        with open(wav_path, "wb") as f:
            f.write(synth_res.content)
            
        # winsoundで再生
        winsound.PlaySound(wav_path, winsound.SND_FILENAME)
        
        if os.path.exists(wav_path):
            os.remove(wav_path)
    except Exception:
        pass

@app.route('/')
def index():
    return render_template_string(HTML_UI)

@app.route('/api/chat', methods=['POST'])
def chat_api():
    global current_model_index
    data = request.json
    user_message = data.get("message", "")
    
    switch_notice = change_model(user_message)
    if switch_notice:
        speak_voicevox(switch_notice)
        return jsonify({"response": switch_notice, "current_model": MODEL_STAIRS[current_model_index]})
    
    if MODEL_STAIRS[current_model_index] == "gemini":
        ai_response = chat_with_gemini(user_message)
    else:
        ai_response = chat_with_ollama(user_message)
        
    speak_voicevox(ai_response)
    auto_git_sync(mode="save")
    
    return jsonify({"response": ai_response, "current_model": MODEL_STAIRS[current_model_index]})

import os
import time

def is_voicevox_running():
    try:
        output = subprocess.check_output(["tasklist"], text=True)
        return "VOICEVOX.exe" in output
    except Exception:
        return False

def launch_voicevox():
    #voicevox_path = os.path.expanduser(r"~\AppData\Local\Programs\VOICEVOX\VOICEVOX.exe")
    voicevox_path = r"C:\Program Files\VOICEVOX\VOICEVOX.exe"
    if os.path.exists(voicevox_path):
        subprocess.Popen([voicevox_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(5)
    else:
        pass

def is_ollama_running():
    try:
        # tasklistコマンドでOllamaが動いているかチェック
        output = subprocess.check_output(["tasklist"], text=True)
        return "ollama" in output.lower()
    except Exception:
        return False

def launch_ollama():
    # Ollamaのインストールパスを確認（通常は以下の場所です）
    ollama_path = os.path.expanduser(r"~\AppData\Local\Programs\Ollama\ollama.exe")
    if os.path.exists(ollama_path):
        # バックグラウンドで起動
        subprocess.Popen([ollama_path, "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(10) # 起動完了まで少し待機

def main():
    auto_git_sync(mode="start")
    
    # Ollamaが動いていなければ起動
    if not is_ollama_running():
        launch_ollama()

    if not is_voicevox_running():
        launch_voicevox()
        
    print(f"システム起動完了。現在のモデル: {MODEL_STAIRS[current_model_index]}")
    app.run(host='0.0.0.0', port=5000, debug=False)

if __name__ == "__main__":
    main()

