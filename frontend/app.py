import subprocess
import sys
from pathlib import Path


def launch_if_run_directly():
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx
        if get_script_run_ctx(suppress_warning=True) is not None:
            return
    except ModuleNotFoundError as error:
        if error.name != "streamlit":
            raise

    project_root = Path(__file__).resolve().parents[1]
    python = project_root / ".venv" / "bin" / "python"
    if not python.is_file():
        python = Path(sys.executable)
    raise SystemExit(subprocess.call(
        [str(python), "-m", "streamlit", "run", str(Path(__file__).resolve())],
        cwd=project_root,
    ))


if __name__ == "__main__":
    launch_if_run_directly()

import requests, streamlit as st

st.set_page_config(page_title="DocMind",page_icon="📄",layout="wide")

try:
    API=st.secrets.get("API_URL","http://localhost:8000")
except FileNotFoundError:
    API="http://localhost:8000"

for k,v in {"token":None,"guest_id":None,"user":None,"workspace_id":None,"chat_id":None}.items():
    st.session_state.setdefault(k,v)

def headers():
    h={}
    if st.session_state.token: h["Authorization"]=f"Bearer {st.session_state.token}"
    elif st.session_state.guest_id: h["X-Guest-Id"]=st.session_state.guest_id
    return h

def api(method,path,**kwargs):
    kwargs.setdefault("headers",headers())
    try:
        r=requests.request(method,API+path,timeout=(5,240),**kwargs)
    except requests.Timeout as error:
        raise RuntimeError("The API request timed out. Check the backend terminal and try again.") from error
    except requests.ConnectionError as error:
        raise RuntimeError("Cannot connect to the API. Start the backend with '.venv/bin/python -m uvicorn backend.main:app --reload'.") from error
    if r.status_code==401 and st.session_state.token:
        st.session_state.token=None; st.session_state.user=None
        st.error("Session expired. Please sign in again."); st.stop()
    if not r.ok:
        try: msg=r.json().get("detail",r.text)
        except Exception: msg=r.text
        raise RuntimeError(msg)
    return r.json() if r.content else {}

st.title("DocMind")
st.caption("Private document intelligence with grounded answers and citations")

if not st.session_state.token and not st.session_state.guest_id:
    tab1,tab2,tab3=st.tabs(["Sign in","Create account","Continue as guest"])
    with tab1:
        e=st.text_input("Email",key="le"); p=st.text_input("Password",type="password",key="lp")
        if st.button("Sign in"):
            try:
                d=api("POST","/auth/login",json={"email":e,"password":p}); st.session_state.token=d["access_token"]
                st.session_state.user=api("GET","/auth/me"); st.rerun()
            except Exception as x: st.error(str(x))
    with tab2:
        e=st.text_input("Email",key="re"); p=st.text_input("Password",type="password",key="rp")
        if st.button("Create account"):
            try:
                d=api("POST","/auth/register",json={"email":e,"password":p}); st.session_state.token=d["access_token"]
                st.session_state.user=api("GET","/auth/me"); st.rerun()
            except Exception as x: st.error(str(x))
    with tab3:
        if st.button("Start guest session"):
            try:
                d=api("POST","/workspaces",json={"name":"Guest workspace"})
                st.session_state.guest_id=d["guest_id"]; st.session_state.workspace_id=d["id"]; st.rerun()
            except Exception as x: st.error(str(x))
    st.stop()

with st.sidebar:
    st.subheader("Account")
    st.write(st.session_state.user["email"] if st.session_state.user else "Guest")
    if st.button("Logout / end session"):
        for k in ["token","guest_id","user","workspace_id","chat_id"]: st.session_state[k]=None
        st.rerun()

if st.session_state.token:
    try:
        workspaces=api("GET","/workspaces")
    except Exception as x:
        st.error(str(x)); workspaces=[]
    st.sidebar.subheader("Workspaces")
    for x in workspaces:
        if st.sidebar.button(f"{x['name']} · {x['documents']} docs",key=x["id"]):
            st.session_state.workspace_id=x["id"]; st.session_state.chat_id=None
    new_name=st.sidebar.text_input("New workspace")
    if st.sidebar.button("Create workspace") and new_name.strip():
        try:
            d=api("POST","/workspaces",json={"name":new_name.strip()}); st.session_state.workspace_id=d["id"]; st.rerun()
        except Exception as x: st.error(str(x))

if not st.session_state.workspace_id:
    st.info("Create or select a workspace to begin.")
    st.stop()

try: ws=api("GET",f"/workspaces/{st.session_state.workspace_id}")
except Exception as x: st.error(str(x)); st.stop()

st.header(ws["name"])
left,right=st.columns([1,2])

with left:
    st.subheader("Documents")
    f=st.file_uploader("PDF or DOCX",type=["pdf","docx"])
    if f and st.button("Upload & index"):
        try:
            d=api("POST",f"/workspaces/{ws['id']}/documents",files={"file":(f.name,f.getvalue())})
            st.success(f"{d['filename']} indexed"); st.rerun()
        except Exception as x: st.error(str(x))
    for d in ws["documents"]:
        st.write(f"**{d['filename']}** — {d['status']}")
        c1,c2=st.columns(2)
        if c1.button("Summarize",key="s"+d["id"]):
            try: st.info(api("POST",f"/documents/{d['id']}/summary")["summary"])
            except Exception as x: st.error(str(x))
        if c2.button("Questions",key="q"+d["id"]):
            try:
                for q in api("GET",f"/documents/{d['id']}/suggested-questions")["questions"]: st.write("• "+q)
            except Exception as x: st.error(str(x))

with right:
    st.subheader("Chat")
    if not st.session_state.chat_id:
        if ws["chats"]:
            labels={f"{c['title']}":c["id"] for c in ws["chats"]}
            selected=st.selectbox("Previous chats",["New chat"]+list(labels))
            if selected!="New chat": st.session_state.chat_id=labels[selected]
        if st.button("Start new chat"):
            try:
                st.session_state.chat_id=api("POST",f"/workspaces/{ws['id']}/chats")["id"]; st.rerun()
            except Exception as x: st.error(str(x))
    if st.session_state.chat_id:
        try: hist=api("GET",f"/chats/{st.session_state.chat_id}/history")["history"]
        except Exception as x: st.error(str(x)); st.stop()
        for m in hist:
            with st.chat_message("user" if m["role"]=="user" else "assistant"):
                st.markdown(m["content"])
                if m.get("sources"):
                    with st.expander("Sources"):
                        for s in m["sources"]:
                            st.caption(f"{s['file_name']} · page {s.get('page_number') or '-'} · chunk {s['chunk_index']}")
        q=st.chat_input("Ask across this workspace...")
        if q:
            try:
                api("POST",f"/chats/{st.session_state.chat_id}/ask",json={"query":q})
                st.rerun()
            except Exception as x: st.error(str(x))
