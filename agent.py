import sqlite3
import os
import pandas as pd
import google.generativeai as genai
from dotenv import load_dotenv
from DataVault import vault

# 1. 設定 API Key (從 .env 讀取)
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise RuntimeError("找不到 GEMINI_API_KEY，請在 .env 檔案中設定後再執行。")

# 2. 初始化 Gemini
genai.configure(api_key=api_key)

# 設定模型參數
generation_config = {
    "temperature": 0, # 設為 0 讓輸出穩定
    "top_p": 0.95,
    "top_k": 64,
    "max_output_tokens": 8192,
}

SYSTEM_INSTRUCTION = """
你是一個 SQLite 資料庫專家。請根據提供的資料庫 Schema，回答使用者的問題。
規則:
1. 直接輸出 SQL 語法，不要包含 Markdown 標記 (如 ```sql ... ```)。
2. 不要解釋你的思考過程。
3. 確保 SQL 語法符合 SQLite 標準。
"""

try:
    model = genai.GenerativeModel(
        model_name="models/gemini-flash-latest",
        generation_config=generation_config,
        system_instruction=SYSTEM_INSTRUCTION,
    )
except Exception:
    print("找不到 Flash 模型，切換至 gemini-pro")
    model = genai.GenerativeModel(
        model_name="gemini-pro",
        generation_config=generation_config,
        system_instruction=SYSTEM_INSTRUCTION,
    )


def get_db_schema():
    """
    【Schema Linking】動態抓取資料庫結構
    """
    conn = sqlite3.connect('school.db')
    cursor = conn.cursor()

    schema_str = ""
    tables = cursor.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()

    for table in tables:
        table_name = table[0]
        ddl = cursor.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{table_name}';").fetchone()[0]
        schema_str += ddl + "\n"

    conn.close()
    return schema_str


def execute_sql(sql):
    """
    執行 SQL (支援多重指令，並區分讀寫操作)
    """
    conn = sqlite3.connect('school.db')
    cursor = conn.cursor()
    results = []

    try:
        # 1. 依據分號拆分指令
        queries = [q.strip() for q in sql.split(';') if q.strip()]

        for q in queries:
            print(f"正在執行子指令: {q}")

            # 如果是 SELECT 開頭 (不分大小寫)，代表會有回傳資料，用 Pandas
            if q.strip().upper().startswith("SELECT"):
                df = pd.read_sql_query(q, conn)
                results.append(df)

            else:
                cursor.execute(q)
                conn.commit()

                # 回傳一個成功的訊息字串，而不是 DataFrame
                results.append(f"指令執行成功 (受影響行數: {cursor.rowcount})")

        return results

    except Exception as e:
        return f"Error : SQL 執行失敗: {e}"
    finally:
        conn.close()


def generate_sql(user_question):
    schema = get_db_schema()
    prompt = f"""
    【資料庫 Schema】: {schema}
    【使用者問題】: {user_question}
    請生成 SQL (只輸出 SQL，不要有 markdown):
    """
    try:
        response = model.generate_content(prompt)
        sql = response.text.strip().replace("```sql", "").replace("```", "").strip()
        return sql
    except Exception as e:
        # 回傳 None 代表失敗，不要回傳錯誤字串
        print(f"AI 生成錯誤: {e}")
        return None


def clean_sql(text):
    """小工具：清洗 AI 回傳的 SQL"""
    return text.strip().replace("```sql", "").replace("```", "").strip()


def solve_with_correction(user_question):
    schema = get_db_schema()
    MAX_RETRIES = 3 # 設定最多嘗試次數，避免無限迴圈

    # 1. 啟動一個對話 Session (這樣 AI 才知道上下文)
    chat = model.start_chat(history=[])

    # 2. 初始 Prompt
    initial_prompt = f"""
    你是一個 SQLite 資料庫專家。請根據以下的 Schema 回答問題。
    【Schema】: {schema}
    【問題】: {user_question}
    【規則】: 只輸出 SQL，不要解釋。
    """

    print(f"(第 1 次嘗試) 正在生成 SQL...")
    response = chat.send_message(initial_prompt)
    current_sql = clean_sql(response.text)

    # 3. 進入修正迴圈
    for attempt in range(MAX_RETRIES):
        print(f"生成 SQL: {current_sql}")

        # 執行 SQL
        result = execute_sql(current_sql)

        # 檢查結果：如果是 list 代表成功，如果是 str 且開頭是 Error 代表失敗
        if not (isinstance(result, str) and result.startswith("Error")):
            return result # 成功！回傳 DataFrame 列表

        # --- 走到這裡代表出錯了，開始修正 ---
        error_msg = result
        print(f"發現錯誤: {error_msg}")

        if attempt < MAX_RETRIES - 1: # 如果還有重試機會
            print("正在將錯誤訊息回報給 AI 進行修正...")

            correction_prompt = f"""
            你剛剛生成的 SQL 執行失敗了。
            【錯誤 SQL】: {current_sql}
            【錯誤訊息】: {error_msg}

            請根據錯誤訊息修正 SQL。只輸出修正後的 SQL，不要解釋。
            """

            # 把錯誤丟給 AI，請它重寫
            response = chat.send_message(correction_prompt)
            current_sql = clean_sql(response.text)
        else:
            print("達到最大重試次數，放棄修正")
            return error_msg


def solve_with_privacy(user_question):
    # 1. 【Sanitization】去識別化
    # 這裡的 safe_question 裡面已經沒有 "Jason" 了，只有 "[SECRET_VALUE_0]"
    safe_question = vault.sanitize_input(user_question)

    print(f"(傳送給 AI 的問題): {safe_question}")
    # AI 根本沒看過 Jason 這個字，它只知道要查一個代號

    # 2. 生成 SQL (傳入處理過的問題)
    generated_sql = generate_sql(safe_question)

    if generated_sql is None: return "生成失敗"

    print(f"(AI 生成的 SQL): {generated_sql}")
    # 預期 AI 會寫出: SELECT ... WHERE name = '[SECRET_VALUE_0]'

    # 3. 【Desanitization】還原數據
    # 在執行前，把 Token 換回真實數據
    real_sql = vault.desanitize_sql(generated_sql)

    print(f"(還原後的真實 SQL): {real_sql}")
    # 變成: SELECT ... WHERE name = 'Jason'

    # 4. 執行
    return execute_sql(real_sql)


if __name__ == '__main__':
    print("學校資料庫 AI 助理 (Gemini 版) 已啟動！")

    while True:
        question = input("\n請輸入問題: ")
        if question.lower() in ['exit', 'quit']:
            break

        # 取得結果
        results = solve_with_correction(question)

        if results is None:
            print("無法生成 SQL，請重試。")
            continue

        # 2. 如果結果是字串 (String) -> 代表是錯誤訊息
        if isinstance(results, str):
            print(f"執行發生錯誤: {results}")

        # 3. 如果結果是列表 (List) -> 代表有多張表格 (多個 SELECT)
        elif isinstance(results, list):
            print(f"\n查詢完成，共 {len(results)} 個結果:")
            for i, df in enumerate(results):
                print(f"\n--- 結果 {i+1} ---")
                print(df) # Pandas 會漂亮地印出表格

        # 4. 如果結果是 DataFrame (單張表格) -> 針對單一結果的情況
        # hasattr(results, 'empty') 是判斷是否為 DataFrame 的安全方法
        elif hasattr(results, 'empty'):
            print("\n查詢完成:")
            print(results)

        else:
            print("未知的回傳格式")
