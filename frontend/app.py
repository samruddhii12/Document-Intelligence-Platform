import streamlit as st
import requests

BACKEND_URL = "http://127.0.0.1:8000"

st.set_page_config(
    page_title="DocMind — Document Intelligence",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;600;700&family=Plus+Jakarta+Sans:wght@300;400;500;600&display=swap');

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

html, body, [data-testid="stAppViewContainer"] {
    background-color: #F7F5F0;
    color: #1A1814;
    font-family: 'Plus Jakarta Sans', sans-serif;
}

[data-testid="stAppViewContainer"] {
    background-color: #F7F5F0;
    min-height: 100vh;
}

[data-testid="stHeader"] { background: transparent !important; }

.block-container {
    max-width: 780px !important;
    padding: 2.5rem 2rem 6rem !important;
    margin: 0 auto;
}

#MainMenu, footer, [data-testid="stToolbar"],
[data-testid="stDecoration"] { display: none !important; }

/* ── Hero ── */
.hero {
    text-align: center;
    padding: 3rem 0 2.5rem;
    border-bottom: 1.5px solid #E4E0D8;
    margin-bottom: 2.5rem;
}
.hero-badge {
    display: inline-block;
    background: #EEF0FF;
    color: #4B5CF6;
    font-size: 0.65rem;
    font-weight: 600;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    padding: 0.3rem 0.85rem;
    border-radius: 999px;
    margin-bottom: 1.2rem;
    border: 1px solid #D8DCFF;
}
.hero-title {
    font-family: 'Playfair Display', serif;
    font-size: clamp(2.2rem, 5vw, 3.4rem);
    font-weight: 700;
    color: #1A1814;
    line-height: 1.1;
    letter-spacing: -0.02em;
    margin-bottom: 0.7rem;
}
.hero-title em {
    font-style: italic;
    color: #4B5CF6;
}
.hero-sub {
    font-size: 0.88rem;
    color: #7A7468;
    line-height: 1.75;
    font-weight: 400;
}

/* ── Cards ── */
.card {
    background: #FFFFFF;
    border: 1px solid #E4E0D8;
    border-radius: 14px;
    padding: 1.6rem 1.8rem;
    margin-bottom: 1rem;
    position: relative;
}
.card-tag {
    font-size: 0.6rem;
    font-weight: 600;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: #4B5CF6;
    margin-bottom: 0.5rem;
}
.card-title {
    font-family: 'Playfair Display', serif;
    font-size: 1.05rem;
    font-weight: 600;
    color: #1A1814;
    margin-bottom: 0.25rem;
}
.card-desc {
    font-size: 0.75rem;
    color: #9A9490;
    line-height: 1.6;
}
.card-num {
    font-family: 'Playfair Display', serif;
    font-size: 3rem;
    font-weight: 700;
    color: #F0EDE8;
    position: absolute;
    top: 1rem;
    right: 1.5rem;
    line-height: 1;
    user-select: none;
}

/* ── Session pill ── */
.session-pill {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    background: #FFF8F0;
    border: 1px solid #F0DFC8;
    border-radius: 999px;
    padding: 0.28rem 0.85rem;
    font-size: 0.62rem;
    font-weight: 500;
    color: #C07840;
    letter-spacing: 0.05em;
    margin-top: 0.6rem;
}
.session-dot {
    width: 5px;
    height: 5px;
    background: #F0A060;
    border-radius: 50%;
    animation: blink 2s infinite;
}
@keyframes blink {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.3; }
}

/* ── Ready badge ── */
.ready-badge {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    background: #F0FFF6;
    border: 1px solid #C0EDD4;
    border-radius: 999px;
    padding: 0.28rem 0.85rem;
    font-size: 0.62rem;
    font-weight: 600;
    color: #2A8A50;
    letter-spacing: 0.06em;
}
.ready-dot {
    width: 5px;
    height: 5px;
    background: #3ABF6A;
    border-radius: 50%;
}

/* ── Streamlit widget overrides ── */
[data-testid="stFileUploader"] {
    background: #FAFAF8 !important;
    border: 1.5px dashed #D0CCC4 !important;
    border-radius: 10px !important;
    padding: 0.4rem !important;
    transition: border-color 0.2s !important;
}
[data-testid="stFileUploader"]:hover {
    border-color: #4B5CF6 !important;
}
[data-testid="stFileUploader"] label,
[data-testid="stFileUploader"] small,
[data-testid="stFileUploader"] span {
    color: #9A9490 !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    font-size: 0.78rem !important;
}

/* Text input */
[data-testid="stTextInput"] input {
    background: #FFFFFF !important;
    border: 1.5px solid #E4E0D8 !important;
    border-radius: 10px !important;
    color: #1A1814 !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    font-size: 0.85rem !important;
    padding: 0.7rem 1rem !important;
    transition: border-color 0.2s, box-shadow 0.2s !important;
}
[data-testid="stTextInput"] input:focus {
    border-color: #4B5CF6 !important;
    box-shadow: 0 0 0 3px rgba(75,92,246,0.08) !important;
}
[data-testid="stTextInput"] input::placeholder { color: #C0BCB8 !important; }
[data-testid="stTextInput"] label {
    color: #7A7468 !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    font-size: 0.72rem !important;
    font-weight: 500 !important;
    letter-spacing: 0.06em !important;
    text-transform: uppercase !important;
}

/* Buttons */
[data-testid="stButton"] button {
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    font-weight: 600 !important;
    font-size: 0.8rem !important;
    letter-spacing: 0.03em !important;
    border-radius: 9px !important;
    padding: 0.55rem 1.3rem !important;
    border: none !important;
    cursor: pointer !important;
    transition: all 0.15s ease !important;
}
[data-testid="stButton"]:not(:last-child) button {
    background: #4B5CF6 !important;
    color: #fff !important;
    box-shadow: 0 2px 8px rgba(75,92,246,0.25) !important;
}
[data-testid="stButton"] button:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 14px rgba(75,92,246,0.3) !important;
}
[data-testid="stButton"] button:active {
    transform: translateY(0) !important;
}
[data-testid="stButton"]:last-of-type button {
    background: #FFF5F5 !important;
    border: 1px solid #FFCDD0 !important;
    color: #D94040 !important;
    box-shadow: none !important;
}
[data-testid="stButton"]:last-of-type button:hover {
    background: #FFE8E8 !important;
    box-shadow: 0 2px 8px rgba(217,64,64,0.12) !important;
}

/* Alerts */
[data-testid="stAlert"] {
    border-radius: 9px !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    font-size: 0.78rem !important;
    font-weight: 500 !important;
    border: none !important;
}

/* ── Chat bubbles ── */
.chat-wrap {
    display: flex;
    flex-direction: column;
    gap: 1.2rem;
    margin-top: 1rem;
}
.bubble-row {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
}
.bubble-label {
    font-size: 0.6rem;
    font-weight: 600;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    padding: 0 0.2rem;
}
.label-you { color: #4B5CF6; }
.label-ai  { color: #2A8A50; }

.bubble-you {
    align-self: flex-end;
    background: #4B5CF6;
    color: #fff;
    border-radius: 14px 14px 3px 14px;
    padding: 0.75rem 1.1rem;
    font-size: 0.84rem;
    line-height: 1.7;
    max-width: 85%;
    box-shadow: 0 2px 10px rgba(75,92,246,0.2);
}
.bubble-ai {
    align-self: flex-start;
    background: #FFFFFF;
    color: #1A1814;
    border: 1px solid #E4E0D8;
    border-radius: 14px 14px 14px 3px;
    padding: 0.75rem 1.1rem;
    font-size: 0.84rem;
    line-height: 1.75;
    max-width: 90%;
    box-shadow: 0 1px 4px rgba(0,0,0,0.05);
    white-space: pre-wrap;
}
.bubble-time {
    font-size: 0.58rem;
    color: #C0BCB8;
    padding: 0 0.2rem;
}

/* ── Divider ── */
.soft-divider {
    border: none;
    border-top: 1px solid #E4E0D8;
    margin: 1.8rem 0;
}

/* ── Danger zone ── */
.danger-label {
    font-size: 0.6rem;
    font-weight: 600;
    letter-spacing: 0.16em;
    text-transform: uppercase;
    color: #C0BCB8;
    margin-bottom: 0.6rem;
}

/* ── File info ── */
.file-info {
    font-size: 0.74rem;
    color: #9A9490;
    padding: 0.35rem 0;
    display: flex;
    align-items: center;
    gap: 0.4rem;
}
.file-name { color: #1A1814; font-weight: 500; }
.file-size { color: #4B5CF6; }
</style>
""", unsafe_allow_html=True)

# ── Session init ──────────────────────────────────────────────────────────
if "session_id" not in st.session_state:
    st.session_state.session_id = None
if "embedded" not in st.session_state:
    st.session_state.embedded = False
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# ── Restore history on page reload ───────────────────────────────────────
if st.session_state.session_id and not st.session_state.chat_history:
    try:
        r = requests.get(f"{BACKEND_URL}/history/{st.session_state.session_id}")
        st.session_state.chat_history = r.json().get("history", [])
    except Exception:
        pass

# ── Hero ──────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero">
    <div class="hero-badge">📄 AI Document Intelligence</div>
    <div class="hero-title">Ask your <em>documents</em><br>anything.</div>
    <div class="hero-sub">Upload a PDF or Word file and get instant,<br>context-aware answers powered by local AI.</div>
</div>
""", unsafe_allow_html=True)

# ── Step 1: Upload ────────────────────────────────────────────────────────
st.markdown("""
<div class="card">
    <div class="card-num">01</div>
    <div class="card-tag">Step One</div>
    <div class="card-title">Upload Your Document</div>
    <div class="card-desc">PDF and DOCX formats supported. Processed entirely on your machine.</div>
</div>
""", unsafe_allow_html=True)

uploaded_file = st.file_uploader(
    "Drop your file here or click to browse",
    type=["pdf", "docx"],
    label_visibility="visible"
)

if uploaded_file is not None:
    col1, col2 = st.columns([4, 1])
    with col1:
        st.markdown(f"""
        <div class="file-info">
            📎 <span class="file-name">{uploaded_file.name}</span>
            &nbsp;·&nbsp;
            <span class="file-size">{round(uploaded_file.size / 1024, 1)} KB</span>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        if st.button("Upload →", key="upload_btn"):
            with st.spinner("Uploading & indexing…"):
                files = {"file": (uploaded_file.name, uploaded_file.getvalue())}
                try:
                    res = requests.post(f"{BACKEND_URL}/upload", files=files)
                    data = res.json()
                    st.session_state.session_id = data["session_id"]
                    st.session_state.chat_history = []
                    st.session_state.embedded = False

                    requests.post(f"{BACKEND_URL}/embed/{st.session_state.session_id}")
                    st.session_state.embedded = True
                    st.success("Document uploaded and indexed — ready to chat!")
                except Exception as e:
                    st.error(f"Upload failed: {e}")

# Session badge + ready indicator
if st.session_state.session_id:
    col_a, col_b = st.columns([3, 1])
    with col_a:
        st.markdown(f"""
        <div class="session-pill">
            <div class="session-dot"></div>
            SESSION &nbsp;·&nbsp; {st.session_state.session_id[:28]}…
        </div>
        """, unsafe_allow_html=True)
    with col_b:
        if st.session_state.embedded:
            st.markdown("""
            <div class="ready-badge" style="margin-top:0.6rem;">
                <div class="ready-dot"></div>
                Indexed & ready
            </div>
            """, unsafe_allow_html=True)

st.markdown('<hr class="soft-divider">', unsafe_allow_html=True)

# ── Step 2: Ask questions ─────────────────────────────────────────────────
if st.session_state.session_id:
    st.markdown("""
    <div class="card">
        <div class="card-num">02</div>
        <div class="card-tag">Step Two</div>
        <div class="card-title">Ask a Question</div>
        <div class="card-desc">Type your question and press Enter. The AI will answer using only your document.</div>
    </div>
    """, unsafe_allow_html=True)

    if not st.session_state.embedded:
        st.warning("Document is still being indexed. Please wait a moment.")
        st.stop()

    question = st.text_input(
        "Your question",
        placeholder="e.g. Summarize the key findings in section 2",
        label_visibility="visible",
        key="question_input"
    )

    if question:
        with st.spinner("Thinking…"):
            try:
                response = requests.post(
                    f"{BACKEND_URL}/chat/{st.session_state.session_id}",
                    json={"query": question, "top_k": 10}
                )
                result = response.json()

                # Fetch full updated history from backend
                history_res = requests.get(f"{BACKEND_URL}/history/{st.session_state.session_id}")
                st.session_state.chat_history = history_res.json().get("history", [])
            except Exception as e:
                st.error(f"Query failed: {e}")

    # ── Chat history display ───────────────────────────────────────────────
    if st.session_state.chat_history:
        st.markdown('<div class="chat-wrap">', unsafe_allow_html=True)

        for chat in reversed(st.session_state.chat_history):
            ts = chat.get("timestamp", "")
            time_label = ts[11:16] if len(ts) >= 16 else ""

            st.markdown(f"""
            <div class="bubble-row">
                <div class="bubble-label label-you">You</div>
                <div class="bubble-you">{chat["question"]}</div>
                <div class="bubble-time">{time_label}</div>
            </div>
            <div class="bubble-row">
                <div class="bubble-label label-ai">DocMind</div>
                <div class="bubble-ai">{chat["answer"]}</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<hr class="soft-divider">', unsafe_allow_html=True)

# ── Danger zone ───────────────────────────────────────────────────────────
if st.session_state.session_id:
    st.markdown('<div class="danger-label">Danger Zone</div>', unsafe_allow_html=True)

    if st.button("🗑 Delete Session & Clear Data", key="delete_btn"):
        try:
            requests.delete(f"{BACKEND_URL}/session/{st.session_state.session_id}")
        except Exception:
            pass
        st.session_state.session_id = None
        st.session_state.embedded = False
        st.session_state.chat_history = []
        st.success("Session cleared.")
        st.rerun()
        