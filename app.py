# Reload timestamp: 2023-05-17 15:30:00  # Updated timestamp to force reload
import streamlit as st
import os
import pandas as pd
from datetime import datetime
import random
import string
import time
import logging

# 添加调试信息
logging.basicConfig(level=logging.DEBUG, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                   filename='/workspaces/QUIZ_NEW/app_debug.log')
logging.debug("应用程序启动")

# 导入项目模块
from database import Database, get_api_key
from llm import AIService
from utils import (
    generate_class_code,
    generate_student_id,
    format_time,
    validate_input,
)

# 初始化数据库
db = Database()

# 配置页面
st.set_page_config(
    page_title="智能教育工具",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 添加自定义CSS
def load_css():
    st.markdown("""
    <style>
    /* 全局字体设置 */
    * {
        font-family: 'Noto Sans', sans-serif;
    }
    
    h1, h2, h3 {
        font-family: 'Source Han Sans CN', 'Noto Sans CJK SC', sans-serif;
        font-weight: bold;
    }
    
    /* 按钮样式 */
    .stButton>button {
        min-height: 40px;
        min-width: 40px;
    }
    
    /* 输入框样式 */
    .stTextInput>div>div>input {
        min-height: 40px;
    }
    
    /* 错误提示样式 */
    .error-box {
        border: 2px solid red;
        border-radius: 5px;
        padding: 10px;
        margin: 10px 0;
        background-color: #ffeeee;
    }
    
    /* 计数器样式 */
    .word-counter {
        text-align: right;
        font-size: 0.8em;
        color: #888;
    }
    
    /* 评分样式 */
    .score-display {
        font-size: 1.2em;
        font-weight: bold;
    }
    
    /* 反馈样式 */
    .feedback-box {
        background-color: #f0f8ff;
        border-radius: 5px;
        padding: 15px;
        margin: 10px 0;
    }
    
    /* 学生列表样式 */
    .student-list {
        max-height: 300px;
        overflow-y: auto;
        border: 1px solid #ddd;
        border-radius: 5px;
        padding: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

load_css()

# 初始化会话状态
if 'user_type' not in st.session_state:
    # Check if user_type is in query params first
    if "user_type" in st.query_params:
        st.session_state.user_type = st.query_params["user_type"]
    else:
        st.session_state.user_type = None
        
if 'class_code' not in st.session_state:
    # Check if class_code is in query params first
    if "class_code" in st.query_params:
        st.session_state.class_code = st.query_params["class_code"]
    else:
        st.session_state.class_code = None
        
if 'student_id' not in st.session_state:
    # Check if student_id is in query params first
    if "student_id" in st.query_params:
        st.session_state.student_id = st.query_params["student_id"]
    else:
        st.session_state.student_id = None
        
if 'current_question' not in st.session_state:
    st.session_state.current_question = None
if 'timer_active' not in st.session_state:
    st.session_state.timer_active = False
if 'time_remaining' not in st.session_state:
    st.session_state.time_remaining = 0
if 'answer_submitted' not in st.session_state:
    st.session_state.answer_submitted = False
if 'evaluation_result' not in st.session_state:
    st.session_state.evaluation_result = None
if 'connected_students' not in st.session_state:
    st.session_state.connected_students = []

def teacher_view():
    """教师控制台视图"""
    st.title("教师控制台 👨‍🏫")
    
    # 创建选项卡
    tab1, tab2, tab3 = st.tabs(["问题创建", "课堂管理", "数据导出"])
    
    # 问题创建选项卡
    with tab1:
        st.header("创建讨论问题")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("手动输入问题")
            question_text = st.text_area("输入问题:", height=150)
            if st.button("使用此问题", key="manual_question"):
                if validate_input(question_text, min_length=10):
                    st.session_state.current_question = question_text
                    st.success("问题已设置!")
                else:
                    st.error("问题太短或为空，请输入有效的问题。")
        
        with col2:
            st.subheader("AI生成问题")
            subject = st.selectbox("学科:", ["科学", "数学", "文学", "历史", "地理", "艺术", "通用"])
            difficulty = st.select_slider("难度:", options=["简单", "中等", "困难"])
            keywords = st.text_input("关键词(用逗号分隔):")
            
            if st.button("生成问题", key="ai_question"):
                with st.spinner("AI正在生成问题..."):
                    # 转换为英文参数
                    subject_mapping = {
                        "科学": "science", "数学": "math", "文学": "literature", 
                        "历史": "history", "地理": "geography", "艺术": "art", "通用": "general"
                    }
                    
                    difficulty_mapping = {
                        "简单": "easy", "中等": "medium", "困难": "hard"
                    }
                    
                    # 准备参数
                    params = {
                        "subject": subject_mapping.get(subject, "general"),
                        "difficulty": difficulty_mapping.get(difficulty, "medium"),
                        "keywords": [k.strip() for k in keywords.split(",") if k.strip()]
                    }
                    
                    try:
                        generated_question = AIService.generate_question(params)
                        st.session_state.current_question = generated_question
                        st.success("问题生成成功!")
                        st.write(generated_question)
                    except Exception as e:
                        st.error(f"生成问题失败: {e}")
                        st.info("已切换到预设问题库")
                        # 使用预设问题
                        default_questions = {
                            "science": "解释牛顿第三定律在日常生活中的应用。",
                            "math": "如何在不使用公式的情况下解释勾股定理？",
                            "literature": "分析文学作品中象征手法的重要性。",
                            "history": "探讨工业革命对现代社会的影响。",
                            "general": "分析批判性思维在解决问题中的作用。"
                        }
                        subject_key = subject_mapping.get(subject, "general")
                        st.session_state.current_question = default_questions.get(subject_key, default_questions["general"])
                        st.write(st.session_state.current_question)
    
    # 课堂管理选项卡
    with tab2:
        st.header("课堂管理")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.session_state.class_code:
                st.subheader(f"当前课堂码: {st.session_state.class_code}")
                
                # 显示当前问题
                if st.session_state.current_question:
                    st.write("**当前问题:**")
                    st.info(st.session_state.current_question)
                else:
                    st.warning("尚未设置讨论问题。请在“问题创建”选项卡中创建问题。")
                
                # 计时器控制
                col_timer1, col_timer2 = st.columns(2)
                with col_timer1:
                    timer_minutes = st.number_input("答题时间(分钟):", min_value=1, max_value=60, value=5)
                with col_timer2:
                    if not st.session_state.timer_active:
                        if st.button("开始计时"):
                            st.session_state.time_remaining = timer_minutes * 60
                            st.session_state.timer_active = True
                    else:
                        if st.button("停止计时"):
                            st.session_state.timer_active = False
                
                # 显示剩余时间
                if st.session_state.timer_active:
                    st.write(f"剩余时间: {format_time(st.session_state.time_remaining)}")
                
                # 结束课堂按钮
                if st.button("结束课堂", type="primary"):
                    st.session_state.class_code = None
                    st.session_state.current_question = None
                    st.session_state.timer_active = False
                    st.session_state.connected_students = []
                    # Update URL parameters to reflect state changes
                    st.query_params.class_code = ""  # Remove class_code from URL
            else:
                st.subheader("创建新课堂")
                
                if not st.session_state.current_question:
                    st.warning("请先在'问题创建'选项卡中创建问题。")
                    st.stop()
                
                if st.button("生成课堂码", type="primary"):
                    new_code = generate_class_code()
                    # 保存到数据库
                    if db.create_classroom(new_code, "teacher-1", st.session_state.current_question):
                        st.session_state.class_code = new_code
                        st.success(f"课堂创建成功! 课堂码: {new_code}")
                        # Set class_code in URL for sharing/bookmarking
                        st.query_params.class_code = new_code
                    else:
                        st.error("创建课堂失败，请重试。")
        
        with col2:
            st.subheader("已连接学生")
            
            if st.session_state.class_code:
                # 从数据库刷新学生列表
                st.session_state.connected_students = db.get_classroom_students(st.session_state.class_code)
                
                st.write(f"连接学生数: {len(st.session_state.connected_students)}")
                
                # 显示学生列表
                if st.session_state.connected_students:
                    st.markdown('<div class="student-list">', unsafe_allow_html=True)
                    for i, student in enumerate(st.session_state.connected_students):
                        st.write(f"{i+1}. {student['id']} (加入时间: {student['joined_at']})")
                    st.markdown('</div>', unsafe_allow_html=True)
                else:
                    st.info("暂无学生连接")
            else:
                st.info("创建课堂后此处将显示连接的学生")
    
    # 数据导出选项卡
    with tab3:
        st.header("数据导出")
        
        if st.session_state.class_code:
            st.write(f"当前课堂: {st.session_state.class_code}")
            
            # 获取课堂数据
            try:
                df = db.get_classroom_data(st.session_state.class_code)
                if not df.empty:
                    st.write("课堂数据预览:")
                    st.dataframe(df.head())
                    
                    # 导出选项
                    export_format = st.selectbox("导出格式:", ["CSV", "Excel"])
                    
                    if st.button("导出数据", type="primary"):
                        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                        filename = f"classroom_{st.session_state.class_code}_{timestamp}"
                        
                        if export_format == "CSV":
                            file_path = f"{filename}.csv"
                            df.to_csv(file_path, index=False)
                        else:
                            file_path = f"{filename}.xlsx"
                            df.to_excel(file_path, index=False)
                        
                        # 生成下载链接
                        with open(file_path, "rb") as file:
                            st.download_button(
                                label="下载文件",
                                data=file,
                                file_name=os.path.basename(file_path),
                                mime="application/octet-stream"
                            )
                else:
                    st.info("暂无数据可供导出")
            except Exception as e:
                st.error(f"获取数据失败: {e}")
        else:
            st.info("请先创建或加入课堂")

def student_view():
    """学生终端视图"""
    st.title("学生终端 👨‍🎓")
    
    # 如果尚未加入课堂
    if not st.session_state.class_code:
        st.header("加入课堂")
        
        col1, col2 = st.columns(2)
        
        with col1:
            class_code = st.text_input("输入课堂码:", max_chars=4).upper()
            
            if st.button("加入", type="primary"):
                if len(class_code) == 4:
                    # 生成学生ID并加入课堂
                    student_id = generate_student_id()
                    
                    # 保存到数据库
                    if db.add_student(student_id, class_code):
                        st.session_state.class_code = class_code
                        st.session_state.student_id = student_id
                        # Update URL parameters for state persistence
                        st.query_params.class_code = class_code
                        st.query_params.student_id = student_id
                    else:
                        st.error("加入课堂失败，请检查课堂码是否正确。")
                else:
                    st.error("课堂码必须是4个字符")
        
        with col2:
            st.info("提示: 请向教师获取课堂码")
    
    # 已加入课堂
    else:
        st.header(f"已加入课堂: {st.session_state.class_code}")
        st.subheader(f"你的ID: {st.session_state.student_id}")
        
        # 显示倒计时（如果有）
        if st.session_state.timer_active and st.session_state.time_remaining > 0:
            st.warning(f"剩余时间: {format_time(st.session_state.time_remaining)}")
        
        # 从数据库获取当前问题
        # 实际应用中应该有一个机制从教师端获取问题
        # 这里简化为当用户加入课堂时就设置问题
        if not st.session_state.current_question:
            # 模拟从数据库获取问题
            # 实际应用中应该有实时更新机制
            question = "这是一个示例问题。实际应用中，应从课堂数据库获取问题。"
            st.session_state.current_question = question
        
        # 显示问题
        st.write("**讨论问题:**")
        st.info(st.session_state.current_question)
        
        # 如果尚未提交答案
        if not st.session_state.answer_submitted:
            st.subheader("你的回答:")
            
            # 使用Markdown编辑器
            answer_text = st.text_area("在此输入你的回答(支持Markdown):", height=200)
            
            # 显示字数统计
            st.markdown(f'<div class="word-counter">{len(answer_text)} 字</div>', unsafe_allow_html=True)
            
            col1, col2 = st.columns([1, 3])
            
            with col1:
                if st.button("提交回答", type="primary", disabled=not answer_text.strip()):
                    if validate_input(answer_text, min_length=10):
                        with st.spinner("正在评估你的回答..."):
                            try:
                                # 调用AI评估
                                eval_result = AIService.evaluate_answer(
                                    st.session_state.current_question, 
                                    answer_text
                                )
                                
                                # 保存回答和评估结果
                                db.save_answer(
                                    st.session_state.student_id,
                                    st.session_state.class_code,
                                    st.session_state.current_question,
                                    answer_text,
                                    eval_result
                                )
                                
                                st.session_state.answer_submitted = True
                                st.session_state.evaluation_result = eval_result
                            except Exception as e:
                                st.error(f"评估失败: {e}")
                    else:
                        st.error("答案太短，请提供更详细的回答。")
            
            with col2:
                st.info("提示: 提交后将收到AI反馈，并且不能修改答案。")
        
        # 已提交答案，显示评估结果
        else:
            st.subheader("你的回答已提交")
            
            if st.session_state.evaluation_result:
                # 显示评分
                score = st.session_state.evaluation_result.get('score', 0)
                score_percentage = int(score * 100)
                
                st.markdown(f'<div class="score-display">评分: {score_percentage}%</div>', unsafe_allow_html=True)
                
                # 显示反馈
                st.markdown('### 反馈')
                st.markdown(f'<div class="feedback-box">{st.session_state.evaluation_result.get("feedback", "无反馈")}</div>', unsafe_allow_html=True)
                
                # 显示建议
                st.markdown('### 改进建议')
                suggestions = st.session_state.evaluation_result.get('suggestions', [])
                for i, suggestion in enumerate(suggestions):
                    st.write(f"{i+1}. {suggestion}")
            else:
                st.info("评估结果不可用")
            
            # 退出课堂按钮
            if st.button("退出课堂"):
                st.session_state.class_code = None
                st.session_state.student_id = None
                st.session_state.current_question = None
                st.session_state.answer_submitted = False
                st.session_state.evaluation_result = None
                # Clear the URL parameters
                st.query_params.clear()

def main():
    """主应用函数"""
    logging.debug("进入 main() 函数")
    
    # 侧边栏
    with st.sidebar:
        st.title("智能教育工具")
        st.write("基于AI的课堂讨论助手")
        
        # 如果尚未选择用户类型
        if not st.session_state.user_type:
            st.header("选择用户类型")
            
            # 修改：使用一列布局，让按钮更明显
            st.write("### 请选择你的身份:")
            
            if st.button("👨‍🏫 教师端", key="teacher_btn", use_container_width=True):
                st.session_state.user_type = "teacher"
                st.query_params.user_type = "teacher"
            
            st.write("") # 添加一些间距
            
            if st.button("👨‍🎓 学生端", key="student_btn", use_container_width=True):
                st.session_state.user_type = "student"
                st.query_params.user_type = "student"
                
            # 添加调试信息
            st.write("---")
            st.info("如果您看不到按钮，请刷新页面或清除浏览器缓存")
        
        # 如果已选择用户类型
        if st.session_state.user_type:
            st.write(f"学生ID: {st.session_state.student_id}")
            
            # 切换用户类型按钮
            if st.button("切换用户类型"):
                st.session_state.user_type = None
                st.session_state.class_code = None
                st.session_state.student_id = None
                st.session_state.current_question = None
                st.session_state.answer_submitted = False
                st.session_state.evaluation_result = None
                # Clear URL parameters
                st.query_params.clear()
        
        # 添加一些应用信息
        st.markdown("---")
        st.write("📚 智能教育工具 v1.0")
        st.write("⚙️ 基于Python + Streamlit + AI")
        st.write("© 2025 教育科技")
    
    # 检查AI API是否可用
    logging.debug("检查 AI API 是否可用...")
    api_available = AIService.is_api_available()
    logging.debug(f"AI API 可用性检查结果: {api_available}")
    if not api_available:
        st.error("⚠️ AI服务不可用。请检查以下内容：\n"
                 "1. 确保网络连接正常。\n"
                 "2. 检查API密钥是否正确。\n"
                 "3. 确保AI服务端点可访问。")
    else:
        st.success("✅ AI服务连接正常")
    
    # 根据用户类型显示不同的视图
    if st.session_state.user_type == "teacher":
        teacher_view()
    elif st.session_state.user_type == "student":
        student_view()
    else:
        # 欢迎页面
        st.title("欢迎使用智能教育工具")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("教师功能")
            st.write("✅ 问题创建与管理")
            st.write("✅ 课堂实时监控")
            st.write("✅ 学生回答数据分析")
            st.write("✅ AI辅助教学评估")
        
        with col2:
            st.subheader("学生功能")
            st.write("✅ 简单的课堂连接")
            st.write("✅ Markdown格式回答")
            st.write("✅ 实时AI反馈")
            st.write("✅ 个性化学习建议")
        
        st.info("请在左侧边栏选择您的用户类型")

# 启动应用
if __name__ == "__main__":
    main()
    
    # 更新计时器（如果激活）
    if st.session_state.timer_active and st.session_state.time_remaining > 0:
        # 在实际应用中，应该使用前端JavaScript或其他方式实现更精确的计时
        # 这里使用一个简化的方法
        st.session_state.time_remaining -= 1
        time.sleep(1)