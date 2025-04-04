import sqlite3
import json
import os
from datetime import datetime
import pandas as pd

# Define the get_api_key function directly in database.py
def get_api_key(section: str, key: str) -> str:
    """从credentials文件中读取指定的API密钥"""
    print(f"==== Debug: get_api_key called with section={section}, key={key} ====")
    credentials_path = "/workspaces/QUIZ_NEW/credentials"
    
    # 确保只处理 DEEPSEEK 部分，彻底删除 OPENROUTER 相关代码
    if section != "DEEPSEEK":
        raise ValueError(f"不支持的配置部分: [{section}]，仅支持 [DEEPSEEK]")
    
    if key != "DEEPSEEK_API_KEY":
        raise ValueError(f"不支持的密钥: {key}，仅支持 DEEPSEEK_API_KEY")
    
    # 检查凭证文件
    if not os.path.exists(credentials_path):
        print(f"Creating default credentials file at {credentials_path}")
        with open(credentials_path, "w") as f:
            f.write("[DEEPSEEK]\n")
            f.write("DEEPSEEK_API_KEY = sk-ef9f0d89a2b24958bf5a6223c167813a\n")
    
    if not os.path.exists(credentials_path):
        raise FileNotFoundError(f"Credentials file not found at {credentials_path}")
    
    # Print debugging information
    print(f"==== Debug: Reading credentials from: {credentials_path} ====")
    print(f"Looking for section: [{section}], key: {key}")
    
    with open(credentials_path, "r") as f:
        lines = f.readlines()
        in_section = False
        for line in lines:
            line = line.strip()
            if not line or line.startswith("#"):  # Skip empty lines and comments
                continue
            if line.startswith(f"[{section}]"):
                in_section = True
            elif line.startswith("[") and in_section:
                in_section = False  # We've moved to a new section
            elif in_section and line.startswith(key):
                parts = line.split("=", 1)
                if len(parts) == 2:
                    return parts[1].strip()
    
    # If we reach here, we couldn't find the key
    print(f"==== Debug: Key {key} not found in section {section} ====")
    
    # 只针对 DEEPSEEK API 处理默认值
    if section == "DEEPSEEK" and key == "DEEPSEEK_API_KEY":
        print("==== Debug: Using default DEEPSEEK_API_KEY ====")
        return "sk-ef9f0d89a2b24958bf5a6223c167813a"
    
    raise ValueError(f"{key} not found in section [{section}]")

class Database:
    def __init__(self, db_path="education_tool.db"):
        """初始化数据库连接"""
        self.db_path = db_path
        self.initialize_db()
    
    def initialize_db(self):
        """创建必要的表结构"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 创建课堂表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS classrooms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            class_code TEXT UNIQUE,
            created_at TIMESTAMP,
            teacher_id TEXT,
            question TEXT,
            status TEXT
        )
        ''')
        
        # 创建学生表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT UNIQUE,
            class_code TEXT,
            joined_at TIMESTAMP,
            FOREIGN KEY (class_code) REFERENCES classrooms (class_code)
        )
        ''')
        
        # 创建回答表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS answers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT,
            class_code TEXT,
            question TEXT,
            answer TEXT,
            score REAL,
            feedback TEXT,
            suggestions TEXT,
            submitted_at TIMESTAMP,
            FOREIGN KEY (student_id) REFERENCES students (student_id),
            FOREIGN KEY (class_code) REFERENCES classrooms (class_code)
        )
        ''')
        
        conn.commit()
        conn.close()
    
    def create_classroom(self, class_code, teacher_id, question):
        """创建新的课堂"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "INSERT INTO classrooms (class_code, created_at, teacher_id, question, status) VALUES (?, ?, ?, ?, ?)",
                (class_code, datetime.now(), teacher_id, question, "active")
            )
            conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"数据库错误: {e}")
            return False
        finally:
            conn.close()
    
    def add_student(self, student_id, class_code):
        """向课堂添加学生"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "INSERT INTO students (student_id, class_code, joined_at) VALUES (?, ?, ?)",
                (student_id, class_code, datetime.now())
            )
            conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"数据库错误: {e}")
            return False
        finally:
            conn.close()
    
    def save_answer(self, student_id, class_code, question, answer, evaluation):
        """保存学生回答和评估"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                """INSERT INTO answers 
                (student_id, class_code, question, answer, score, feedback, suggestions, submitted_at) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    student_id, 
                    class_code, 
                    question, 
                    answer, 
                    evaluation['score'], 
                    evaluation['feedback'], 
                    json.dumps(evaluation['suggestions']), 
                    datetime.now()
                )
            )
            conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"数据库错误: {e}")
            return False
        finally:
            conn.close()
    
    def get_classroom_students(self, class_code):
        """获取课堂中的学生列表"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT student_id, joined_at FROM students WHERE class_code = ?",
            (class_code,)
        )
        students = cursor.fetchall()
        conn.close()
        
        return [{"id": s[0], "joined_at": s[1]} for s in students]
    
    def get_classroom_data(self, class_code):
        """获取课堂所有数据，用于导出"""
        conn = sqlite3.connect(self.db_path)
        
        try:
            # Use parameterized query to prevent SQL injection
            query = """
            SELECT s.student_id, a.question, a.answer, a.score, a.feedback, a.suggestions, a.submitted_at
            FROM answers a
            JOIN students s ON a.student_id = s.student_id
            WHERE a.class_code = ?
            ORDER BY a.submitted_at
            """
            
            df = pd.read_sql_query(query, conn, params=(class_code,))
            return df
        except Exception as e:
            print(f"获取课堂数据失败: {e}")
            return pd.DataFrame()  # Return empty DataFrame on error
        finally:
            conn.close()
    
    def export_to_csv(self, class_code, file_path):
        """导出课堂数据到CSV"""
        df = self.get_classroom_data(class_code)
        if df.empty:
            return False
        try:
            df.to_csv(file_path, index=False)
            return os.path.exists(file_path)
        except Exception as e:
            print(f"导出CSV失败: {e}")
            return False