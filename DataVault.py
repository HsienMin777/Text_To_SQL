import re
import uuid

class DataVault:
    def __init__(self):
        # 這是一個暫存的查找表 (Session-based Lookup Table)
        # 用來暫存 { "[PERSON_1]": "Jason" }
        self.token_map = {} 
        
        # 定義我們要保護的敏感關鍵字 (在真實系統中，這裡通常接 NER 模型或資料庫白名單)
        # 這裡為了演示，我們先手動列出「敏感名單」
        self.sensitive_data = ["Jason", "Alice", "Bob", "Judy", "0912-345-678"]

    def sanitize_input(self, user_question):
        """
        【上行加密】將使用者問題中的敏感字替換為 Token
        User: "幫我查 Jason 的成績" -> Prompt: "幫我查 [PERSON_1] 的成績"
        """
        sanitized_text = user_question
        self.token_map = {} # 每次新的問題都重置 Map
        
        for idx, secret in enumerate(self.sensitive_data):
            # 如果發現敏感字出現在問題中
            if secret in user_question:
                # 生成一個 Token，例如 [SECRET_VALUE_0]
                token = f"[SECRET_VALUE_{idx}]"
                
                # 記錄到保險箱：記得 [SECRET_VALUE_0] 其實是 Jason
                self.token_map[token] = secret
                
                # 替換文字
                sanitized_text = sanitized_text.replace(secret, token)
        
        return sanitized_text

    def desanitize_sql(self, generated_sql):

        real_sql = generated_sql
        for token, original_value in self.token_map.items():
            # 將 Token 換回原始值
            real_sql = real_sql.replace(token, original_value)
            
        return real_sql

# 初始化金庫
vault = DataVault()