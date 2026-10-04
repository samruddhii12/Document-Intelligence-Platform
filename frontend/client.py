import requests
import streamlit as st


def base_url():
    # Avoid Streamlit rendering a missing-secrets error before a fallback can run.
    from pathlib import Path
    import os
    configured=os.getenv("API_URL")
    if configured: return configured.rstrip("/")
    if Path('.streamlit/secrets.toml').exists() or (Path.home()/'.streamlit/secrets.toml').exists():
        return st.secrets.get("API_URL","http://127.0.0.1:8000").rstrip("/")
    return "http://127.0.0.1:8000"


def headers():
    if st.session_state.token: return {"Authorization":"Bearer "+st.session_state.token}
    if st.session_state.guest_id: return {"X-Guest-Id":st.session_state.guest_id}
    return {}


def api(method,path,**kwargs):
    kwargs.setdefault("headers",headers())
    try:
        response=requests.request(method,base_url()+path,timeout=(5,240),**kwargs)
        if response.status_code==401 and st.session_state.token and st.session_state.refresh_token and path!="/auth/refresh":
            refreshed=requests.request("POST",base_url()+"/auth/refresh",json={"refresh_token":st.session_state.refresh_token},timeout=(5,15))
            if refreshed.ok:
                data=refreshed.json(); st.session_state.token=data["access_token"]; st.session_state.refresh_token=data["refresh_token"]
                kwargs["headers"]={**kwargs["headers"],"Authorization":"Bearer "+data["access_token"]}
                response=requests.request(method,base_url()+path,timeout=(5,240),**kwargs)
        if response.status_code==401:
            st.session_state.token=None; st.session_state.refresh_token=None; st.session_state.user=None
            st.session_state.guest_id=None; st.session_state.workspace_id=None; st.session_state.chat_id=None
        if not response.ok:
            try: message=response.json().get("detail",response.text)
            except ValueError: message=response.text
            raise RuntimeError(str(message))
        return response.json() if response.content else {}
    except requests.Timeout as error:
        raise RuntimeError("The API request timed out. Check the API and worker terminals.") from error
    except requests.ConnectionError as error:
        raise RuntimeError("Cannot connect to the API. Start '.venv/bin/python -m uvicorn backend.main:app --reload'.") from error


def download(path):
    try:
        response=requests.get(base_url()+path,headers=headers(),timeout=(5,30))
        if not response.ok: raise RuntimeError("Download unavailable. Refresh your session and try again.")
        return response.content
    except requests.RequestException as error:
        raise RuntimeError("Could not download the original file") from error


def signed_in(data):
    if st.session_state.guest_id: st.session_state.pending_guest=st.session_state.guest_id
    st.session_state.token=data["access_token"]; st.session_state.refresh_token=data["refresh_token"]
    st.session_state.guest_id=None; st.session_state.workspace_id=None; st.session_state.chat_id=None
    st.session_state.user=api("GET","/auth/me")
