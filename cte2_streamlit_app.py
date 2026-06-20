# ===== cte2_streamlit_app.py (带朗读功能 v2) =====
import streamlit as st
import streamlit.components.v1 as components
import requests
import re

if "GITHUB_TOKEN" not in st.secrets:
    GITHUB_TOKEN = st.sidebar.text_input("请输入您的 GitHub Token（github_pat_...）", type="password")
else:
    GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
if not GITHUB_TOKEN:
    st.warning("请先设置 GitHub Token（侧边栏或 Secrets）")
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

st.set_page_config(page_title="指定结构AI出题练习程序", page_icon="🎙️")
st.title("🎙️ 指定结构AI出题练习程序")
st.markdown("---")

# ---------- 语音组件 ----------
def voice_component():
    html = """
    <div style="margin:8px 0; display:flex; align-items:center; gap:10px;">
        <button id="voiceBtn" onclick="toggleVoice()" style="
            padding:10px 20px; font-size:16px; border:none; border-radius:6px;
            background-color:#4CAF50; color:white; cursor:pointer;
        ">🎤 开始录音</button>
        <span id="voiceStatus" style="color:#666;">点击后说话</span>
    </div>
    <script>
    var rec = null;
    var isRecording = false;
    function toggleVoice() {
        var btn = document.getElementById('voiceBtn');
        var status = document.getElementById('voiceStatus');
        if (isRecording) {
            if (rec) { rec.stop(); rec = null; }
            isRecording = false;
            btn.innerText = '🎤 开始录音';
            btn.style.backgroundColor = '#4CAF50';
            return;
        }
        var SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRecognition) { status.innerText = '❌ 浏览器不支持'; return; }
        rec = new SpeechRecognition();
        rec.lang = 'en-US';
        rec.interimResults = false;
        rec.continuous = false;
        rec.onresult = function(event) {
            var transcript = event.results[0][0].transcript;
            status.innerText = '✅ ' + transcript;
            var textareas = document.querySelectorAll('textarea');
            if (textareas.length > 0) {
                var ta = textareas[textareas.length - 1];
                ta.value = transcript;
                ta.dispatchEvent(new Event('input', { bubbles: true }));
            }
            try {
                if (window.Streamlit) window.Streamlit.setComponentValue(transcript);
                else if (parent && parent.Streamlit) parent.Streamlit.setComponentValue(transcript);
            } catch(e) {}
            btn.innerText = '🎤 开始录音';
            btn.style.backgroundColor = '#4CAF50';
            isRecording = false;
        };
        rec.onerror = function(event) {
            status.innerText = '❌ 错误: ' + event.error;
            btn.innerText = '🎤 开始录音';
            btn.style.backgroundColor = '#4CAF50';
            isRecording = false;
        };
        rec.onend = function() {
            if (isRecording) {
                isRecording = false;
                btn.innerText = '🎤 开始录音';
                btn.style.backgroundColor = '#4CAF50';
            }
        };
        rec.start();
        isRecording = true;
        btn.innerText = '⏹ 停止录音';
        btn.style.backgroundColor = '#f44336';
        status.innerText = '🎙️ 录音中...';
    }
    </script>
    """
    components.html(html, height=80)
    return

# ---------- 中文朗读按钮（components.html 独立渲染）----------
def chinese_tts_button(text):
    safe_text = text.replace("'", "\\'").replace("\n", " ").strip()
    html = f"""
    <div>
        <button id="ttsBtn" onclick="speakNow()" style="
            padding:4px 14px; font-size:14px; border:none; border-radius:4px;
            background-color:#2196F3; color:white; cursor:pointer;
        ">🔊 朗读</button>
    </div>
    <script>
    function speakNow() {{
        try {{
            var text = '{safe_text}';
            var utterance = new SpeechSynthesisUtterance(text);
            utterance.lang = 'zh-CN';
            utterance.rate = 0.9;
            utterance.pitch = 1.0;
            window.speechSynthesis.cancel(); // 防止重叠
            window.speechSynthesis.speak(utterance);
            console.log('朗读开始: ' + text);
        }} catch(e) {{
            console.error('朗读错误: ' + e);
        }}
    }}
    </script>
    """
    components.html(html, height=40)

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
    # 中文题目 + 朗读按钮（并排）
    col1, col2 = st.columns([10, 1])
    with col1:
        st.info(f"中文：{sentences[idx]}")
    with col2:
        chinese_tts_button(sentences[idx])  # 朗读按钮

    voice_component()  # 语音按钮

    user_english = st.text_area("输入您的英文句子（语音识别结果自动填入）",
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
            st.rerun()
