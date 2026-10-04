import subprocess
import sys
from pathlib import Path


def launch_if_run_directly():
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx
        if get_script_run_ctx(suppress_warning=True) is not None: return
    except ModuleNotFoundError as error:
        if error.name!="streamlit": raise
    root=Path(__file__).resolve().parents[1]
    python=root/".venv"/"bin"/"python"
    raise SystemExit(subprocess.call([str(python) if python.exists() else sys.executable,"-m","streamlit","run",str(Path(__file__).resolve())],cwd=root))

if __name__=="__main__": launch_if_run_directly()

import streamlit as st
from frontend.client import api
from frontend.views import account, documents, analysis

st.set_page_config(page_title="DocMind — Document & Data Intelligence",page_icon="📄",layout="wide")
for key in ["token","refresh_token","guest_id","pending_guest","user","workspace_id","chat_id","dataset_id","google_url","google_handoff"]:
    st.session_state.setdefault(key,None)
st.title("DocMind")
st.caption("Document answers with citations · Reproducible data analysis")
try:
    account.render()
    workspaces=api("GET","/workspaces")
    st.sidebar.subheader("Workspaces")
    for workspace in workspaces:
        if st.sidebar.button(f"{workspace['name']} · {workspace['documents']} docs · {workspace['datasets']} datasets",key="workspace-"+workspace["id"]):
            st.session_state.workspace_id=workspace["id"]; st.session_state.chat_id=None; st.session_state.dataset_id=None; st.rerun()
    if not st.session_state.workspace_id and workspaces: st.session_state.workspace_id=workspaces[0]["id"]
    with st.sidebar.form("new-workspace"):
        name=st.text_input("New workspace")
        submitted=st.form_submit_button("Create workspace")
    if submitted:
        result=api("POST","/workspaces",json={"name":name.strip()})
        st.session_state.workspace_id=result["id"]; st.session_state.chat_id=None; st.session_state.dataset_id=None; st.rerun()
    if not st.session_state.workspace_id:
        st.info("Create a workspace to begin."); st.stop()
    workspace=api("GET",f"/workspaces/{st.session_state.workspace_id}")
    st.header(workspace["name"])
    document_tab,data_tab=st.tabs(["Document Intelligence","Data Analysis"])
    with document_tab: documents.render(workspace)
    with data_tab: analysis.render(workspace)
except Exception as error:
    st.error(str(error))
