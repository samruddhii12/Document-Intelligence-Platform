import streamlit as st
import requests

BACKEND_URL = "http://127.0.0.1:8000"

st.set_page_config(
    page_title="DocMind — Document Intelligence",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ── Custom CSS ──────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;500;600;700;800&family=DM+Mono:ital,wght@0,300;0,400;0,500;1,300&display=swap');

/* ── Reset & Base ── */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

html, body, [data-testid="stAppViewContainer"] {
    background-color: #0A0A0F;
    color: #E8E6E0;
    font-family: 'DM Mono', monospace;
}

[data-testid="stAppViewContainer"] {
    background:
        radial-gradient(ellipse 80% 50% at 20% -10%, rgba(99,71,255,0.12) 0%, transparent 60%),
        radial-gradient(ellipse 60% 40% at 85% 10%, rgba(255,107,53,0.07) 0%, transparent 50%),
        #0A0A0F;
    min-height: 100vh;
}

[data-testid="stHeader"] { background: transparent !important; }

.block-container {
    max-width: 860px !important;
    padding: 3rem 2rem 6rem !important;
    margin: 0 auto;
}

/* ── Hide Streamlit default elements ── */
#MainMenu, footer, [data-testid="stToolbar"],
[data-testid="stDecoration"] { display: none !important; }

/* ── Typography ── */
h1, h2, h3 { font-family: 'Syne', sans-serif; }

/* ── Hero Header ── */
.hero {
    text-align: center;
    padding: 3.5rem 0 2.5rem;
    position: relative;
}
.hero-eyebrow {
    font-family: 'DM Mono', monospace;
    font-size: 0.65rem;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    color: #6347FF;
    margin-bottom: 1.1rem;
}
.hero-title {
    font-family: 'Syne', sans-serif;
    font-size: clamp(2.4rem, 6vw, 4rem);
    font-weight: 800;
    line-height: 1.0;
    letter-spacing: -0.03em;
    color: #F2F0EA;
    margin-bottom: 0.8rem;
}
.hero-title span {
    background: linear-gradient(135deg, #6347FF 0%, #FF6B35 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}
.hero-sub {
    font-size: 0.8rem;
    color: #7A7870;
    letter-spacing: 0.04em;
    line-height: 1.7;
}
.hero-divider {
    width: 40px;
    height: 1px;
    background: linear-gradient(90deg, #6347FF, #FF6B35);
    margin: 1.8rem auto 0;
}

/* ── Section Cards ── */
.section-card {
    background: rgba(255,255,255,0.028);
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 16px;
    padding: 1.8rem 2rem;
    margin-bottom: 1.2rem;
    position: relative;
    overflow: hidden;
    transition: border-color 0.2s;
}
.section-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 1px;
    background: linear-gradient(90deg, transparent, rgba(99,71,255,0.4), transparent);
}
.section-label {
    font-family: 'DM Mono', monospace;
    font-size: 0.6rem;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: #6347FF;
    margin-bottom: 0.9rem;
    display: flex;
    align-items: center;
    gap: 0.5rem;
}
.section-label::after {
    content: '';
    flex: 1;
    height: 1px;
    background: rgba(99,71,255,0.2);
}
.section-title {
    font-family: 'Syne', sans-serif;
    font-size: 1.1rem;
    font-weight: 700;
    color: #F2F0EA;
    margin-bottom: 0.3rem;
}
.section-desc {
    font-size: 0.72rem;
    color: #7A7870;
    margin-bottom: 1.2rem;
    line-height: 1.6;
}

/* ── Status Badge ── */
.status-badge {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    font-family: 'DM Mono', monospace;
    font-size: 0.65rem;
    letter-spacing: 0.08em;
    padding: 0.3rem 0.75rem;
    border-radius: 999px;
    margin-bottom: 1rem;
}
.status-active {
    background: rgba(99,71,255,0.12);
    border: 1px solid rgba(99,71,255,0.3);
    color: #A28EFF;
}
.status-dot {
    width: 5px;
    height: 5px;
    border-radius: 50%;
    background: #6347FF;
    animation: pulse 2s infinite;
}
@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.3; }
}

/* ── Streamlit widget overrides ── */
[data-testid="stFileUploader"] {
    background: rgba(99,71,255,0.04) !important;
    border: 1.5px dashed rgba(99,71,255,0.25) !important;
    border-radius: 12px !important;
    padding: 0.5rem !important;
    transition: border-color 0.2s !important;
}
[data-testid="stFileUploader"]:hover {
    border-color: rgba(99,71,255,0.5) !important;
}
[data-testid="stFileUploader"] label,
[data-testid="stFileUploader"] small,
[data-testid="stFileUploader"] span {
    color: #7A7870 !important;
    font-family: 'DM Mono', monospace !important;
    font-size: 0.75rem !important;
}

/* Text input */
[data-testid="stTextInput"] input {
    background: rgba(255,255,255,0.04) !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    border-radius: 10px !important;
    color: #E8E6E0 !important;
    font-family: 'DM Mono', monospace !important;
    font-size: 0.82rem !important;
    padding: 0.7rem 1rem !important;
    transition: border-color 0.2s !important;
}
[data-testid="stTextInput"] input:focus {
    border-color: rgba(99,71,255,0.5) !important;
    box-shadow: 0 0 0 3px rgba(99,71,255,0.08) !important;
}
[data-testid="stTextInput"] input::placeholder { color: #4A4844 !important; }
[data-testid="stTextInput"] label {
    color: #7A7870 !important;
    font-family: 'DM Mono', monospace !important;
    font-size: 0.68rem !important;
    letter-spacing: 0.1em !important;
    text-transform: uppercase !important;
}

/* Buttons */
[data-testid="stButton"] button {
    font-family: 'Syne', sans-serif !important;
    font-weight: 600 !important;
    font-size: 0.78rem !important;
    letter-spacing: 0.06em !important;
    border-radius: 10px !important;
    padding: 0.6rem 1.4rem !important;
    border: none !important;
    cursor: pointer !important;
    transition: all 0.18s ease !important;
}

/* Primary buttons */
[data-testid="stButton"]:not(:last-child) button,
[data-testid="stButton"] button[kind="primary"] {
    background: linear-gradient(135deg, #6347FF 0%, #5038E0 100%) !important;
    color: #fff !important;
    box-shadow: 0 4px 14px rgba(99,71,255,0.3) !important;
}
[data-testid="stButton"] button:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 6px 20px rgba(99,71,255,0.4) !important;
}
[data-testid="stButton"] button:active {
    transform: translateY(0) !important;
}

/* Delete button — last button on page */
[data-testid="stButton"]:last-of-type button {
    background: rgba(255,70,70,0.08) !important;
    border: 1px solid rgba(255,70,70,0.2) !important;
    color: #FF7070 !important;
    box-shadow: none !important;
}
[data-testid="stButton"]:last-of-type button:hover {
    background: rgba(255,70,70,0.14) !important;
    box-shadow: 0 4px 14px rgba(255,70,70,0.15) !important;
}

/* Success / Info / Error messages */
[data-testid="stAlert"] {
    border-radius: 10px !important;
    font-family: 'DM Mono', monospace !important;
    font-size: 0.75rem !important;
    border: none !important;
}
.stSuccess {
    background: rgba(40,200,120,0.08) !important;
    color: #5DEBA0 !important;
}
.stInfo {
    background: rgba(99,71,255,0.08) !important;
    color: #A28EFF !important;
}

/* Answer box */
.answer-block {
    background: rgba(99,71,255,0.06);
    border: 1px solid rgba(99,71,255,0.18);
    border-left: 3px solid #6347FF;
    border-radius: 0 12px 12px 0;
    padding: 1.2rem 1.5rem;
    font-size: 0.82rem;
    line-height: 1.85;
    color: #D8D6D0;
    margin-top: 0.8rem;
    font-family: 'DM Mono', monospace;
    white-space: pre-wrap;
}

/* Step number decorators */
.step-number {
    font-family: 'Syne', sans-serif;
    font-size: 2rem;
    font-weight: 800;
    color: rgba(99,71,255,0.12);
    position: absolute;
    top: 1rem;
    right: 1.5rem;
    line-height: 1;
    user-select: none;
}

/* Session ID pill */
.session-pill {
    display: inline-block;
    background: rgba(255,107,53,0.08);
    border: 1px solid rgba(255,107,53,0.2);
    border-radius: 999px;
    padding: 0.25rem 0.8rem;
    font-family: 'DM Mono', monospace;
    font-size: 0.65rem;
    color: #FF9A6C;
    letter-spacing: 0.06em;
    margin-bottom: 1rem;
}

/* Dividers */
hr { border: none; border-top: 1px solid rgba(255,255,255,0.05); margin: 0.5rem 0; }
</style>
""", unsafe_allow_html=True)

# ── Session init ──────────────────────────────────────────────────────────
if "session_id" not in st.session_state:
    st.session_state.session_id = None
if "embedded" not in st.session_state:
    st.session_state.embedded = False

# ── Hero ──────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero">
    <div class="hero-eyebrow">◈ AI-Powered Document Analysis</div>
    <div class="hero-title">Doc<span>Mind</span></div>
    <div class="hero-sub">Upload any document. Ask anything.<br>Get precise, context-aware answers instantly.</div>
    <div class="hero-divider"></div>
</div>
""", unsafe_allow_html=True)

# ── Step 1: Upload ────────────────────────────────────────────────────────
st.markdown("""
<div class="section-card">
    <div class="step-number">01</div>
    <div class="section-label">Step One</div>
    <div class="section-title">Upload Document</div>
    <div class="section-desc">Supports PDF and DOCX formats. Your document is processed locally.</div>
</div>
""", unsafe_allow_html=True)

with st.container():
    uploaded_file = st.file_uploader(
        "Drop your file here or click to browse",
        type=["pdf", "docx"],
        label_visibility="visible"
    )

    if uploaded_file is not None:
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(f"""
            <div style="font-family:'DM Mono',monospace;font-size:0.72rem;color:#7A7870;padding:0.4rem 0;">
                📎 &nbsp;<span style="color:#D8D6D0;">{uploaded_file.name}</span>
                &nbsp;&nbsp;·&nbsp;&nbsp;
                <span style="color:#A28EFF;">{round(uploaded_file.size/1024, 1)} KB</span>
            </div>
            """, unsafe_allow_html=True)
        with col2:
            if st.button("Upload →", key="upload_btn"):
                with st.spinner(""):
                    files = {"file": (uploaded_file.name, uploaded_file.getvalue())}
                    try:
                        response = requests.post(f"{BACKEND_URL}/upload", files=files)
                        data = response.json()
                        st.session_state.session_id = data["session_id"]
                        st.session_state.embedded = False
                        st.success("Document uploaded successfully")
                    except Exception as e:
                        st.error(f"Upload failed: {e}")

# Show session badge
if st.session_state.session_id:
    st.markdown(f"""
    <div style="margin-top:0.6rem;">
        <span class="session-pill">SESSION · {st.session_state.session_id[:24]}…</span>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<hr style='margin:1.5rem 0;'>", unsafe_allow_html=True)

# ── Step 2: Process ───────────────────────────────────────────────────────
if st.session_state.session_id:
    st.markdown("""
    <div class="section-card">
        <div class="step-number">02</div>
        <div class="section-label">Step Two</div>
        <div class="section-title">Process & Index</div>
        <div class="section-desc">Generate semantic embeddings so the AI can search your document intelligently.</div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns([3, 1])
    with col1:
        if st.session_state.embedded:
            st.markdown("""
            <div class="status-badge status-active">
                <div class="status-dot"></div>
                Document indexed and ready
            </div>
            """, unsafe_allow_html=True)
    with col2:
        if st.button("Generate Embeddings →", key="embed_btn"):
            with st.spinner(""):
                try:
                    response = requests.post(f"{BACKEND_URL}/embed/{st.session_state.session_id}")
                    st.session_state.embedded = True
                    st.success("Embeddings generated — document ready")
                except Exception as e:
                    st.error(f"Processing failed: {e}")

    st.markdown("<hr style='margin:1.5rem 0;'>", unsafe_allow_html=True)

# ── Step 3: Chat ──────────────────────────────────────────────────────────
if st.session_state.session_id:
    st.markdown("""
    <div class="section-card">
        <div class="step-number">03</div>
        <div class="section-label">Step Three</div>
        <div class="section-title">Ask Questions</div>
        <div class="section-desc">Ask anything about your document in plain language.</div>
    </div>
    """, unsafe_allow_html=True)

    question = st.text_input(
        "Your question",
        placeholder="e.g. What are the key findings in section 3?",
        label_visibility="visible"
    )

    if st.button("Ask DocMind →", key="ask_btn") and question:
        with st.spinner(""):
            try:
                response = requests.post(
                    f"{BACKEND_URL}/chat/{st.session_state.session_id}",
                    json={"query": question, "top_k": 3}
                )
                result = response.json()
                st.markdown(f"""
                <div class="answer-block">{result["answer"]}</div>
                """, unsafe_allow_html=True)
            except Exception as e:
                st.error(f"Query failed: {e}")

    st.markdown("<hr style='margin:2rem 0 1rem;'>", unsafe_allow_html=True)

# ── Delete ────────────────────────────────────────────────────────────────
if st.session_state.session_id:
    st.markdown("""
    <div style="font-family:'DM Mono',monospace;font-size:0.62rem;letter-spacing:0.12em;
         text-transform:uppercase;color:#4A4844;margin-bottom:0.6rem;">
        Danger Zone
    </div>
    """, unsafe_allow_html=True)

    if st.button("Delete Session & Clear Data", key="delete_btn"):
        try:
            requests.delete(f"{BACKEND_URL}/session/{st.session_state.session_id}")
        except Exception:
            pass
        st.session_state.session_id = None
        st.session_state.embedded = False
        st.success("Session cleared")
        st.rerun()