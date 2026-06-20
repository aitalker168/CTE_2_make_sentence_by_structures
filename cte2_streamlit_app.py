# ===== cte2_streamlit_app.py (稳定版 v2) =====
import streamlit as st
import streamlit.components.v1 as components
import requests
import re

# ---------- GitHub Token ----------
if "GITHUB_TOKEN" not in st.secrets:
    GITHUB_TOKEN = st.sidebar.text_input("请输入您的 GitHub Token（github_pat_...）", type="password")
else:
    GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]

if not GITHUB_TOKEN:
    st.warning("请先设置 GitHub Token（侧边栏或 Secrets）")
    st.stop()

HEADERS = {"Authorization": f"Bearer {GITHUB_TOKEN}", "Content-Type": "application/json"}
API_URL = "https://models.inference.ai.azure.com/chat/completions"

def call_ai(system: str, user: str, temp=0.5, max_tokens=2000, timeout=60):
    payload = {
        "model": "gpt-4o-mini",
        "messages": [{"role":"system","content":system},{"role":"user","content":user}],
        "temperature":temp, "max_tokens":max_tokens
    }
    try:
        resp = requests.post(API_URL, json=payload, headers=HEADERS, timeout=timeout)
        if resp.status_code == 200:
            return resp.json()["choices"][0]["message"]["content"].strip()
        return f"[API错 {resp.status_code}]"
    except Exception as e:
        return f"[网络错] {e}"

# ---------- Prompt ----------
GEN_PROMPT = (
    "你是一个英语句型出题教练。用户给你一个英语句型结构，请生成5个中文句子，每个句子必须能用该句型翻译成英文，且尽量使用简单的日常词汇。\n"
    "输出格式：\n1. 第一个中文句子\n2. 第二个中文句子\n3. 第三个中文句子\n4. 第四个中文句子\n5. 第五个中文句子\n直接输出，不要多余解释。"
)

REV_PROMPT = (
    "你是一个英语句型训练教练。用户给你一个中文句子和用户说出的英文句子。"
    "请检查英文句子是否正确地使用了指定句型，以及语法是否正确。\n"
    "输出格式要求：\n"
    "句子X: [正确/错误]\n"
    "如果正确：\n  反馈: (鼓励，并说明为什么正确)\n"
    "  练习题 (3道关于这个句子的选择题或填空题，用于加深记忆)：\n"
    "    题目1. ...\n    正确答案: (答案)\n"
    "    题目2. ...\n    正确答案: (答案)\n"
    "    题目3. ...\n    正确答案: (答案)\n"
    "如果错误：\n  错误原因: (解释哪里错了，应该怎么修改)\n"
    "  修改建议: (给出正确的句子)\n"
    "  加强练习题 (3道针对该错误的巩固题)：\n"
    "    题目1. ...\n    正确答案: (答案)\n"
    "    题目2. ...\n    正确答案: (答案)\n"
    "    题目3. ...\n    正确答案: (答案)\n"
    "注意：所有题目必须基于该句子，用简单单词。\n"
    "务必严格按照以上格式输出，每道练习题后面紧跟一行以“正确答案:”开头的答案。"
)

# ---------- 会话状态 ----------
if "step" not in st.session_state:
    st.session_state.step = 1
    st.session_state.chinese_sentences = []
    st.session_state.current_index = 0
    st.session_state.full_review = ""
    st.session_state.questions_only = ""
    st.session_state.answer_shown = False
    st.session_state.voice_result = ""

st.set_page_config(page_title="指定结构AI出题练习程序", page_icon="🎙️")
st.title("🎙️ 指定结构AI出题练习程序（语音版）")
st.markdown("---")

# ---------- 语音组件（返回识别文本）----------
def voice_input_component(key_suffix: str):
    """嵌入语音识别按钮，返回识别文本"""
    html_code = f"""
    <div style="margin:8px 0; display:flex; align-items:center; gap:10px;">
        <button id="voiceBtn_{key_suffix}" style="
            padding:10px 20px; font-size:16px; border:none; border-radius:6px;
            background-color:#4CAF50; color:white; cursor:pointer;
        ">🎤 开始录音</button>
        <span id="voiceStatus_{key_suffix}" style="color:#666;">点击后说话</span>
    </div>
    <script>
    (function() {{
        const btn = document.getElementById('voiceBtn_{key_suffix}');
        const status = document.getElementById('voiceStatus_{key_suffix}');
        let recognition = null;
        let isRecording = false;

        btn.onclick = function() {{
            if (isRecording) {{
                if (recognition) {{
                    recognition.stop();
                    recognition = null;
                }}
                isRecording = false;
                btn.innerText = '🎤 开始录音';
                btn.style.backgroundColor = '#4CAF50';
                status.innerText = '已停止';
                return;
            }}
            const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
            if (!SpeechRecognition) {{
                status.innerText = '❌ 浏览器不支持，请用 Chrome/Edge';
                return;
            }}
            recognition = new SpeechRecognition();
            recognition.lang = 'en-US';
            recognition.interimResults = false;
            recognition.continuous = false;

            recognition.onresult = function(event) {{
                const transcript = event.results[0][0].transcript;
                status.innerText = '✅ ' + transcript;
                // 通过 setComponentValue 传回
                if (window.Streamlit) {{
                    window.Streamlit.setComponentValue(transcript);
                }} else if (parent && parent.Streamlit) {{
                    parent.Streamlit.setComponentValue(transcript);
                }}
                btn.innerText = '🎤 开始录音';
                btn.style.backgroundColor = '#4CAF50';
                isRecording = false;
            }};
            recognition.onerror = function(event) {{
                status.innerText = '❌ 错误: ' + event.error;
                btn.innerText = '🎤 开始录音';
                btn.style.backgroundColor = '#4CAF50';
                isRecording = false;
            }};
            recognition.onend = function() {{
                if (isRecording) {{
                    isRecording = false;
                    btn.innerText = '🎤 开始录音';
                    btn.style.backgroundColor = '#4CAF50';
                }}
            }};
            recognition.start();
            isRecording = true;
            btn.innerText = '⏹ 停止录音';
            btn.style.backgroundColor = '#f44336';
            status.innerText = '🎙️ 录音中...';
        }};
    }})();
    </script>
    """
    result = components.html(html_code, height=100)
    return result

# ---------- 第一步 ----------
if st.session_state.step == 1:
    st.header("第一步：输入指定句型结构")
    structure = st.text_input("请输入英语句型结构（如 as...as, not only...but also 等）", placeholder="例如：as...as")
    if st.button("生成5个中文题目", type="primary"):
        if not structure:
            st.error("请输入句型结构")
        else:
            with st.spinner("正在生成题目..."):
                text = call_ai(GEN_PROMPT, f"句型结构：{structure}", temp=0.3, max_tokens=500)
            if text.startswith("["):
                st.error(text)
            else:
                lines = [l.strip() for l in text.split('\n') if l.strip()]
                sentences = []
                for line in lines:
                    line_clean = re.sub(r'^\d+[.、]\s*', '', line)
                    if line_clean:
                        sentences.append(line_clean)
                while len(sentences) < 5:
                    sentences.append("")
                st.session_state.chinese_sentences = sentences
                st.session_state.current_index = 0
                st.session_state.voice_result = ""
                st.session_state.step = 2
                st.rerun()

# ---------- 第二步 ----------
if st.session_state.step == 2:
    st.header("第二步：逐题练习")
    idx = st.session_state.current_index
    sentences = st.session_state.chinese_sentences

    if idx >= 5:
        st.success("🎉 恭喜！5道题全部完成！")
        if st.button("🔄 重新开始"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
        st.stop()

    st.subheader(f"第 {idx+1} / 5 题")
    st.info(f"中文：{sentences[idx]}")

    # 语音按钮
    key = f"voice_{idx}"
    voice_text = voice_input_component(key)

    # 如果语音有返回，保存到 session_state
    if voice_text and voice_text != st.session_state.voice_result:
        st.session_state.voice_result = voice_text
        st.rerun()

    # 文本框（初始值为语音结果）
    default_value = st.session_state.voice_result
    user_english = st.text_area("输入您的英文句子（语音识别结果自动填入）",
                                value=default_value,
                                key=f"english_{idx}",
                                height=80)

    col1, col2, col3 = st.columns([2, 2, 2])
    with col1:
        submit_review = st.button("📤 提交给AI审查", type="primary")
    with col2:
        show_answer = st.button("👁 显示正确答案")
    with col3:
        next_question = st.button("Next →")

    if submit_review:
        if not user_english.strip():
            st.warning("请输入英文")
        else:
            with st.spinner("正在审查..."):
                chinese = sentences[idx]
                user_msg = f"指定句型：\n中文句子：{chinese}\n用户说出的英文句子：{user_english}"
                result = call_ai(REV_PROMPT, user_msg, temp=0.3, max_tokens=2000, timeout=60)
            st.session_state.full_review = result
            lines = result.split('\n')
            question_lines = []
            for line in lines:
                if line.strip().startswith("正确答案:"):
                    continue
                question_lines.append(line)
            st.session_state.questions_only = "\n".join(question_lines).strip()
            st.session_state.answer_shown = False
            st.session_state.voice_result = ""  # 清空，避免影响下一题
            st.rerun()

    if st.session_state.full_review:
        st.markdown("**审查结果与练习题**")
        display_text = st.session_state.full_review if st.session_state.answer_shown else st.session_state.questions_only
        st.text_area("", display_text, height=300)

        if show_answer:
            st.session_state.answer_shown = not st.session_state.answer_shown
            st.rerun()

        if next_question:
            st.session_state.current_index += 1
            st.session_state.full_review = ""
            st.session_state.questions_only = ""
            st.session_state.answer_shown = False
            st.session_state.voice_result = ""
            st.rerun()
