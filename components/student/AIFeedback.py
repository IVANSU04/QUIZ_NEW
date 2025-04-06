import streamlit as st

def render_ai_feedback(evaluation_result):
    """
    渲染AI反馈组件，确保文本清晰可见
    
    Args:
        evaluation_result: 包含score, feedback, suggestions的评估结果字典
    """
    if not evaluation_result:
        st.info("没有可用的评估结果")
        return
    
    # 使用st.container确保所有元素都在一个容器中
    with st.container():
        # 创建带有明确样式的容器
        st.markdown("""
        <style>
        .ai-feedback-container {
            background-color: #f5f5f5;
            border: 1px solid #ddd;
            border-radius: 8px;
            padding: 15px;
            margin: 10px 0;
        }
        .ai-feedback-header {
            color: #2c3e50;
            font-size: 18px;
            font-weight: bold;
            margin-bottom: 10px;
        }
        .ai-feedback-score {
            font-size: 24px;
            font-weight: bold;
            color: #333333;
            margin: 10px 0;
        }
        .ai-feedback-text {
            color: #333333;
            background-color: #ffffff;
            border: 1px solid #e0e0e0;
            border-radius: 5px;
            padding: 10px;
            margin: 10px 0;
        }
        .ai-suggestion-item {
            color: #333333;
            padding: 5px 0;
        }
        </style>
        """, unsafe_allow_html=True)
        
        # 渲染反馈容器
        st.markdown('<div class="ai-feedback-container">', unsafe_allow_html=True)
        
        # 标题
        st.markdown('<div class="ai-feedback-header">AI评估反馈</div>', unsafe_allow_html=True)
        
        # 评分
        score = evaluation_result.get('score', 0)
        score_percentage = int(score * 100)
        st.markdown(f'<div class="ai-feedback-score">评分: {score_percentage}%</div>', unsafe_allow_html=True)
        
        # 反馈
        st.markdown('<strong>详细反馈:</strong>', unsafe_allow_html=True)
        feedback = evaluation_result.get("feedback", "无反馈")
        st.markdown(f'<div class="ai-feedback-text">{feedback}</div>', unsafe_allow_html=True)
        
        # 建议
        st.markdown('<strong>改进建议:</strong>', unsafe_allow_html=True)
        suggestions = evaluation_result.get('suggestions', [])
        if suggestions:
            for i, suggestion in enumerate(suggestions):
                st.markdown(f'<div class="ai-suggestion-item">{i+1}. {suggestion}</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="ai-suggestion-item">没有具体的改进建议</div>', unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
