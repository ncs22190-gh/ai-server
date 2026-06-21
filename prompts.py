import os

RULE_FILE = "rule_flow.txt"
SKILLS_DIR = "skills"

def get_system_prompt(user_text, history):
    # ルールの読み込み
    rule = open(RULE_FILE, "r", encoding="utf-8").read() if os.path.exists(RULE_FILE) else ""
    
    # スキルの動的読み込み
    skills = ""
    if os.path.exists(SKILLS_DIR):
        for f in os.listdir(SKILLS_DIR):
            if f.replace("_skill.txt", "") in user_text:
                with open(os.path.join(SKILLS_DIR, f), "r", encoding="utf-8") as file:
                    skills += f"\n【スキル:{f.replace('_skill.txt', '')}】\n{file.read()}"

    # システムプロンプトの構成
    prompt = f"""
    {rule}
    
    {skills}
    
    【現在の会話履歴】
    {history[-1000:]} 
    
    ユーザー: {user_text}
    """
    return prompt