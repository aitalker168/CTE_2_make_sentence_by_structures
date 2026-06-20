# ===== cte2_streamlit_app.py (可点击+自动填入+布局稳定) =====
import streamlit as st
import streamlit.components.v1 as components
import requests
import re

if "GITHUB_TOKEN" not in st.secrets:
    GITHUB_TOKEN = st.sidebar.text_input("请输入您的 GitHub Token（github_pat_...）", type="password")
else:
    GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
if not GITHUB_TOKEN:
    st.warning("请先设置 Token")
    st.stop()

HEADERS = {"Authorization": f"Bearer {GITHUB_TOKEN}", "Content-Type": "application/json"}
API_URL = "https://models.inference.ai.azure.com/chat/completions"

def call_ai(system, user, temp=0.5, max_tokens=2000, timeout=60):
    payload = {"model": "gpt-4o-mini", "messages": [{"role":"system","content":system},{"role":"user","content":user}], "temperature":temp, "max_tokens":max_tokens}
    try:
        r = requests.post(API_URL, json=payload, headers=HEADERS, timeout=timeout)
        if r.status_code == 200:
            return r.json()["choices"][0]["message"]["content"].strip()
        return f"[API错 {r.status_code}]"
    except Exception as e:
        return f"[网络错] {e}"

GEN_PROMPT = "你是一个英语句型出题教练。用户给你一个英语句型结构，生成5个中文句子，每个句子必须能用该句型翻译成英文，用简单词汇。输出格式：\n1. 第一个中文句子\n2. 第二个\n3. 第三个\n4. 第四个\n5. 第五个\n直接输出。"
REV_PROMPT = "你是一个英语句型训练教练。用户给你一个中文句子和英文句子。检查句型使用和语法。输出格式：\n句子X: [正确/错误]\n如果正确：\n  反馈: (鼓励)\n  练习题 (3道选择/填空)：\n    题目1. ...\n    正确答案: (答案)\n    题目2. ...\n    正确答案: (答案)\n    题目3. ...\n    正确答案: (答案)\n如果错误：\n  错误原因: ...\n  修改建议: (正确句子)\n  加强练习题 (3道)：\n    题目1. ...\n    正确答案: ...\n    题目2. ...\n    正确答案: ...\n    题目3. ...\n    正确答案: ...\n注意：用简单单词，严格按格式。"

if "step" not in st.session_state:
    st.session_state.step=1; st.session_state.sentences=[]; st.session_state.idx=0
    st.session_state.full=""; st.session_state.questions=""; st.session_state.show_answer=False
    st.session_state.voice_result = ""  # 存储语音识别结果

st.set_page_config(page_title="指定结构AI出题练习程序", page_icon="🎙️")
st.title("🎙️ 指定结构AI出题练习程序")
st.markdown("---")

# ---------- 语音组件（返回识别文本）----------
def voice_component(key):
    html = f"""
    <div style="margin:8px 0; display:flex; align-items:center; gap:10px;">
        <button id="voiceBtn_{key}" onclick="startVoice('{key}')" style="
            padding:10px 20px; font-size:16px; border:none; border-radius:6px;
            background-color:#4CAF50; color:white; cursor:pointer;
        ">🎤 开始录音</button>
        <span id="voiceStatus_{key}" style="color:#666;">点击后说话</span>
    </div>
    <script>
    function startVoice(key) {{
        var btn = document.getElementById('voiceBtn_' + key);
        var status = document.getElementById('voiceStatus_' + key);
        if (btn.innerText.includes('停止')) {{
            // 停止录音
            if (window.recognition) {{
                window.recognition.stop();
                window.recognition = null;
            }}
            btn.innerText = '🎤 开始录音';
            btn.style.backgroundColor = '#4CAF50';
            return;
        }}
        var SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRecognition) {{ status.innerText = '❌ 浏览器不支持'; return; }}
        var recognition = new SpeechRecognition();
        recognition.lang = 'en-US';
        recognition.interimResults = false;
        recognition.continuous = false;
        recognition.onresult = function(event) {{
            var transcript = event.results[0][0].transcript;
            status.innerText = '✅ ' + transcript;
            // 通过 setComponentValue 回流
            if (window.Streamlit) window.Streamlit.setComponentValue(transcript);
            else if (parent && parent.Streamlit) parent.Streamlit.setComponentValue(transcript);
            btn.innerText = '🎤 开始录音';
            btn.style.backgroundColor = '#4CAF50';
        }};
        recognition.onerror = function(event) {{
            status.innerText = '❌ 错误: ' + event.error;
            btn.innerText = '🎤 开始录音';
            btn.style.backgroundColor = '#4CAF50';
        }};
        recognition.onend = function() {{
            if (btn.innerText.includes('停止')) {{
                btn.innerText = '🎤 开始录音';
                btn.style.backgroundColor = '#4CAF50';
            }}
        }};
        recognition.start();
        window.recognition = recognition;
        btn.innerText = '⏹ 停止录音';
        btn.style.backgroundColor = '#f44336';
        status.innerText = '🎙️ 录音中...';
    }}
    </script>
    """
    result = components.html(html, height=80)
    return result

# ---------- 第一步 ----------
if st.session_state.step == 1:
    st.header("第一步：输入指定句型结构")
    structure = st.text_input("请输入英语句型结构（如 as...as, not only...but also 等）", placeholder="例如：as...as")
    if st.button("生成5个中文题目", type="primary"):
        if not structure: st.error("请输入句型结构")
        else:
            with st.spinner("生成中..."):
                text = call_ai(GEN_PROMPT, f"句型结构：{structure}")
            if text.startswith("["): st.error(text)
            else:
                lines = [l.strip() for l in text.split('\n') if l.strip()]
                sentences = []
                for line in lines:
                    line_clean = re.sub(r'^\d+[.、]\s*', '', line)
                    if line_clean: sentences.append(line_clean)
                while len(sentences) < 5: sentences.append("")
                st.session_state.sentences = sentences
                st.session_state.idx = 0
                st.session_state.voice_result = ""
                st.session_state.step = 2
                st.rerun()

# ---------- 第二步 ----------
if st.session_state.step == 2:
    st.header("第二步：逐题练习")
    idx = st.session_state.idx
    sentences = st.session_state.sentences

    if idx >= 5:
        st.success("🎉 全部完成！")
        if st.button("🔄 重新开始"):
            for k in list(st.session_state.keys()): del st.session_state[k]
            st.rerun()
        st.stop()

    st.subheader(f"第 {idx+1} / 5 题")
    st.info(f"中文：{sentences[idx]}")

    # 语音组件（返回识别文本）
    voice_result = voice_component(str(idx))

    # 如果语音返回了新文本，更新 session_state，并 rerun 以更新文本框
    if voice_result and voice_result != st.session_state.voice_result:
        st.session_state.voice_result = voice_result
        st.rerun()

    # 文本框：初始值为 session_state.voice_result（语音结果自动显示）
    default_val = st.session_state.voice_result
    user_english = st.text_area("输入您的英文句子（语音识别结果自动填入）",
                                value=default_val,
                                key=f"eng_{idx}",
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
            with st.spinner("审查中..."):
                chinese = sentences[idx]
                user_msg = f"指定句型：\n中文句子：{chinese}\n用户说出的英文句子：{user_english}"
                result = call_ai(REV_PROMPT, user_msg, temp=0.3, max_tokens=2000, timeout=60)
            st.session_state.full = result
            lines = result.split('\n')
            question_lines = []
            for line in lines:
                if line.strip().startswith("正确答案:"):
                    continue
                question_lines.append(line)
            st.session_state.questions = "\n".join(question_lines).strip()
            st.session_state.show_answer = False
            st.session_state.voice_result = ""  # 清空，避免影响下一题
            st.rerun()

    if st.session_state.full:
        st.markdown("**审查结果与练习题**")
        display_text = st.session_state.full if st.session_state.show_answer else st.session_state.questions
        st.text_area("", display_text, height=300)

        if show_answer:
            st.session_state.show_answer = not st.session_state.show_answer
            st.rerun()

        if next_question:
            st.session_state.idx += 1
            st.session_state.full = ""
            st.session_state.questions = ""
            st.session_state.show_answer = False
            st.session_state.voice_result = ""
            st.rerun()
