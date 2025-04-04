import json
import time
import requests
from typing import Dict, List, Any, Optional
import openai  # Import the full module for exceptions
from openai import OpenAI  # Import the OpenAI class for client
import os
import traceback
from database import get_api_key  # Import from database.py
import inspect

class AIService:
    @staticmethod
    def is_api_available() -> bool:
        """检查DeepSeek API是否可用"""
        try:
            print("==== Debug: Starting API availability check with DEEPSEEK ====")
            
            # 获取DeepSeek API密钥
            api_key = get_api_key("DEEPSEEK", "DEEPSEEK_API_KEY")
            print(f"==== Debug: Got DEEPSEEK API key successfully: {api_key[:5]}... ====")
            
            client = OpenAI(
                api_key=api_key, 
                base_url="https://api.deepseek.com/v1"
            )
            
            # 测试API连接
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=5
            )
            print("==== Debug: DeepSeek API test successful ====")
            return True
        except Exception as e:
            print(f"==== Debug: DeepSeek API not available: {str(e)} ====")
            traceback.print_exc()
            return False
    
    @staticmethod
    def generate_quiz(topic: str, difficulty: str, num_questions: int = 5) -> List[Dict[str, Any]]:
        """使用DeepSeek API生成测验问题"""
        try:
            # 只使用DeepSeek API
            api_key = get_api_key("DEEPSEEK", "DEEPSEEK_API_KEY")
            
            client = OpenAI(
                api_key=api_key,
                base_url="https://api.deepseek.com/v1"
            )
            
            # 构建提示
            prompt = f"""
            Generate {num_questions} multiple-choice questions about {topic} at {difficulty} level.
            Each question should have 4 options with only one correct answer.
            Format the response as a JSON array with the following structure for each question:
            {{
                "question": "Question text",
                "options": ["Option A", "Option B", "Option C", "Option D"],
                "answer": "The correct option letter (A, B, C, or D)",
                "explanation": "Explanation of why this answer is correct"
            }}
            """
            
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=2000
            )
            
            # 提取JSON内容
            content = response.choices[0].message.content
            # 查找JSON部分
            json_str = AIService._extract_json(content)
            questions = json.loads(json_str)
            return questions
            
        except Exception as e:
            print(f"AI问题生成失败: {str(e)}")
            traceback.print_exc()
            return []
    
    @staticmethod
    def generate_question(params: Dict[str, Any]) -> str:
        """使用DeepSeek API生成单个讨论问题
        
        Args:
            params: 包含以下键的字典：
                - subject: 主题/学科
                - difficulty: 难度级别
                - keywords: 关键词列表
        
        Returns:
            生成的讨论问题
        """
        try:
            # 获取DeepSeek API密钥
            api_key = get_api_key("DEEPSEEK", "DEEPSEEK_API_KEY")
            
            client = OpenAI(
                api_key=api_key,
                base_url="https://api.deepseek.com/v1"
            )
            
            # 提取参数
            subject = params.get("subject", "general")
            difficulty = params.get("difficulty", "medium")
            keywords = params.get("keywords", [])
            
            # 构建关键词字符串
            keywords_str = ", ".join(keywords) if keywords else "no specific keywords"
            
            # 构建提示
            prompt = f"""
            Generate a thought-provoking discussion question about {subject} at {difficulty} difficulty level.
            The question should incorporate these keywords or concepts if possible: {keywords_str}.
            The question should be clear, open-ended, and designed to encourage critical thinking and classroom discussion.
            Just respond with the question text only, without any additional explanations or formatting.
            """
            
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=500
            )
            
            # 提取生成的问题
            question = response.choices[0].message.content.strip()
            return question
            
        except Exception as e:
            print(f"生成问题失败: {str(e)}")
            traceback.print_exc()
            raise
    
    @staticmethod
    def evaluate_answer(question: str, answer: str) -> Dict[str, Any]:
        """使用DeepSeek API评估学生的回答
        
        Args:
            question: 讨论问题
            answer: 学生的回答
        
        Returns:
            包含评估结果的字典，包括分数、反馈和建议
        """
        try:
            # 获取DeepSeek API密钥
            api_key = get_api_key("DEEPSEEK", "DEEPSEEK_API_KEY")
            
            client = OpenAI(
                api_key=api_key,
                base_url="https://api.deepseek.com/v1"
            )
            
            # 构建提示
            prompt = f"""
            评估学生对以下问题的回答:
            
            问题: {question}
            
            学生回答: {answer}
            
            请按照以下JSON格式提供评估结果:
            ```json
            {{
                "score": 0.85,  // 0到1之间的分数，表示回答质量
                "feedback": "对回答的整体评价",
                "suggestions": [
                    "改进建议1",
                    "改进建议2",
                    "改进建议3"
                ]
            }}
            ```
            
            评估应考虑以下因素:
            1. 回答与问题的相关性
            2. 内容的深度和广度
            3. 论点是否有理有据
            4. 语言表达和逻辑结构
            
            只需返回JSON格式的评估结果，不要包含任何其他文本。
            """
            
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=1000
            )
            
            # 提取评估结果
            evaluation_text = response.choices[0].message.content.strip()
            
            # 提取JSON部分
            json_match = evaluation_text
            # 如果内容包含```json和```标记，需要提取中间部分
            if "```json" in evaluation_text:
                start = evaluation_text.find("```json") + len("```json")
                end = evaluation_text.rfind("```")
                if start != -1 and end != -1:
                    json_match = evaluation_text[start:end].strip()
            
            evaluation = json.loads(json_match)
            
            # 确保评估结果包含所有必要字段
            if "score" not in evaluation:
                evaluation["score"] = 0.5
            if "feedback" not in evaluation:
                evaluation["feedback"] = "评估系统无法生成反馈。"
            if "suggestions" not in evaluation:
                evaluation["suggestions"] = ["没有具体的改进建议。"]
            
            return evaluation
            
        except Exception as e:
            print(f"评估答案失败: {str(e)}")
            traceback.print_exc()
            # 返回默认评估结果，避免完全失败
            return {
                "score": 0.5,
                "feedback": f"评估过程中发生错误: {str(e)}",
                "suggestions": ["请尝试再次提交，或联系教师寻求帮助。"]
            }
    
    @staticmethod
    def _extract_json(text: str) -> str:
        """从文本中提取JSON部分"""
        start = text.find("[")
        end = text.rfind("]") + 1
        if start != -1 and end != 0:
            return text[start:end]
        return "[]"