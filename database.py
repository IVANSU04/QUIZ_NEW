import sqlite3
import json
import os
from datetime import datetime
import pandas as pd

# Define the get_api_key function directly in database.py
def get_api_key(section: str, key: str) -> str:
    """Read specified API key from credentials file"""
    print(f"==== Debug: get_api_key called with section={section}, key={key} ====")
    credentials_path = "/workspaces/QUIZ_NEW/credentials"
    
    # Ensure only DEEPSEEK section is processed, remove OPENROUTER related code
    if section != "DEEPSEEK":
        raise ValueError(f"Unsupported configuration section: [{section}], only [DEEPSEEK] is supported")
    
    if key != "DEEPSEEK_API_KEY":
        raise ValueError(f"Unsupported key: {key}, only DEEPSEEK_API_KEY is supported")
    
    # Check credentials file
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
    
    # Only handle default value for DEEPSEEK API
    if section == "DEEPSEEK" and key == "DEEPSEEK_API_KEY":
        print("==== Debug: Using default DEEPSEEK_API_KEY ====")
        return "sk-ef9f0d89a2b24958bf5a6223c167813a"
    
    raise ValueError(f"{key} not found in section [{section}]")

class Database:
    def __init__(self, db_path=None):
        """Initialize database connection"""
        # Use a fixed absolute path to ensure all sessions use the same database
        if db_path is None:
            self.db_path = "/workspaces/QUIZ_NEW/education_tool.db"
        else:
            self.db_path = db_path
        
        print(f"Using database at: {self.db_path}")
        
        # Don't delete existing database - just initialize if it doesn't exist
        if not os.path.exists(self.db_path):
            print(f"Database file does not exist. Creating new database: {self.db_path}")
            self.initialize_db()
        else:
            # Ensure schema is up to date even for existing database
            self.update_schema_if_needed()
            print(f"Using existing database: {self.db_path}")
    
    def update_schema_if_needed(self):
        """Check and update database schema if needed"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check if tables exist
        try:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='classrooms'")
            if not cursor.fetchone():
                print("Tables don't exist in database. Initializing schema.")
                self.initialize_db()
        except sqlite3.Error as e:
            print(f"Error checking database schema: {e}")
        finally:
            conn.close()
    
    def initialize_db(self):
        """Create necessary table structure"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Enable foreign key constraints
        cursor.execute("PRAGMA foreign_keys = ON")
        
        # Create classrooms table
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
        
        # Create students table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT UNIQUE,
            class_code TEXT,
            joined_at TIMESTAMP,
            FOREIGN KEY (class_code) REFERENCES classrooms (class_code)
        )
        ''')
        
        # Create answers table
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
        """Create a new classroom"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # First check if this class code already exists
            cursor.execute("SELECT COUNT(*) FROM classrooms WHERE class_code = ?", (class_code,))
            if cursor.fetchone()[0] > 0:
                print(f"Class code {class_code} already exists")
                return False
                
            cursor.execute(
                "INSERT INTO classrooms (class_code, created_at, teacher_id, question, status) VALUES (?, ?, ?, ?, ?)",
                (class_code, datetime.now(), teacher_id, question, "active")
            )
            conn.commit()
            print(f"Successfully created classroom with code: {class_code}")
            return True
        except sqlite3.Error as e:
            print(f"Database error in create_classroom: {e}")
            return False
        finally:
            conn.close()
    
    def add_student(self, student_id, class_code):
        """Add a student to a classroom"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Enable foreign key constraints
            cursor.execute("PRAGMA foreign_keys = ON")
            
            # First check if the class code exists - enhanced validation logic
            cursor.execute("SELECT COUNT(*) FROM classrooms WHERE class_code = ?", (class_code,))
            count = cursor.fetchone()[0]
            print(f"Checking class code {class_code}: Found {count} matching classrooms")
            
            if count == 0:
                print(f"Join rejected: Class code {class_code} does not exist in database at {self.db_path}")
                return False
            
            # Check if the classroom is in active status
            cursor.execute("SELECT status FROM classrooms WHERE class_code = ?", (class_code,))
            status = cursor.fetchone()[0]
            if status != "active":
                print(f"Join rejected: Classroom {class_code} has status {status}, not active")
                return False
            
            # Classroom exists and is active, add the student
            try:
                cursor.execute(
                    "INSERT INTO students (student_id, class_code, joined_at) VALUES (?, ?, ?)",
                    (student_id, class_code, datetime.now())
                )
                conn.commit()
                print(f"Student {student_id} successfully joined classroom {class_code}")
                return True
            except sqlite3.IntegrityError as e:
                print(f"Foreign key constraint error: {e} - classroom may not exist")
                return False
        except sqlite3.Error as e:
            print(f"Database error in add_student: {e}")
            return False
        finally:
            conn.close()
    
    def save_answer(self, student_id, class_code, question, answer, evaluation):
        """Save student answer and evaluation"""
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
            print(f"Database error: {e}")
            return False
        finally:
            conn.close()
    
    def get_classroom_students(self, class_code):
        """Get list of students in a classroom"""
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
        """Get all classroom data for export"""
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
            print(f"Failed to get classroom data: {e}")
            return pd.DataFrame()  # Return empty DataFrame on error
        finally:
            conn.close()
    
    def export_to_csv(self, class_code, file_path):
        """Export classroom data to CSV"""
        df = self.get_classroom_data(class_code)
        if df.empty:
            return False
        try:
            df.to_csv(file_path, index=False)
            return os.path.exists(file_path)
        except Exception as e:
            print(f"CSV export failed: {e}")
            return False
    
    def update_classroom_question(self, class_code, question):
        """Update current question for a classroom"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "UPDATE classrooms SET question = ? WHERE class_code = ?",
                (question, class_code)
            )
            conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            return False
        finally:
            conn.close()
    
    def get_classroom_info(self, class_code):
        """Get classroom information including current question"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "SELECT class_code, created_at, teacher_id, question, status FROM classrooms WHERE class_code = ?",
                (class_code,)
            )
            result = cursor.fetchone()
            
            if result:
                return {
                    'class_code': result[0],
                    'created_at': result[1],
                    'teacher_id': result[2],
                    'question': result[3],
                    'status': result[4]
                }
            return None
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            return None
        finally:
            conn.close()
    
    def get_answers_for_question(self, class_code, question):
        """Get all student answers for a specific question in a classroom"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                """SELECT s.student_id, a.answer, a.score, a.feedback, a.suggestions, a.submitted_at 
                FROM answers a
                JOIN students s ON a.student_id = s.student_id
                WHERE a.class_code = ? AND a.question = ?
                ORDER BY a.submitted_at DESC""",
                (class_code, question)
            )
            
            results = cursor.fetchall()
            answers = []
            for row in results:
                answers.append({
                    'student_id': row[0],
                    'answer': row[1],
                    'score': row[2],
                    'feedback': row[3],
                    'suggestions': json.loads(row[4]) if row[4] else [],
                    'submitted_at': row[5]
                })
            
            return answers
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            return []
        finally:
            conn.close()