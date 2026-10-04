import streamlit as st
from frontend.client import api, signed_in


def google_controls(capabilities,link=False):
    if not capabilities.get("google_sign_in"):
        st.caption("Google Sign-In is available after OAuth credentials are configured.")
        return
    label="Link Google" if link else "Start Google Sign-In"
    if st.button(label,key="google-link" if link else "google-login"):
        try:
            data=api("POST","/auth/google/prepare",params={"link":link})
            st.session_state.google_handoff=data["handoff_secret"]
            st.session_state.google_url=data["authorization_url"]
        except Exception as error: st.error(str(error))
    if st.session_state.google_url:
        st.link_button("Continue with Google",st.session_state.google_url)
        st.caption("Complete sign-in in the new tab, then return here.")
        if st.button("Complete Google Sign-In"):
            try:
                data=api("POST","/auth/google/complete",json={"token":st.session_state.google_handoff})
                signed_in(data); st.session_state.google_url=None; st.session_state.google_handoff=None; st.rerun()
            except Exception as error: st.error(str(error))


def forms(capabilities):
    sign_in,register=st.tabs(["Sign in","Create account"])
    with sign_in:
        with st.form("login"):
            email=st.text_input("Email",key="login-email")
            password=st.text_input("Password",type="password",key="login-password")
            submit=st.form_submit_button("Sign in")
        if submit:
            try:
                signed_in(api("POST","/auth/login",json={"email":email,"password":password})); st.rerun()
            except Exception as error: st.error(str(error))
    with register:
        if not capabilities.get("email_verification"):
            st.info("Email registration needs SMTP configuration. You can try the platform as a guest.")
        with st.form("register"):
            email=st.text_input("Email",key="register-email")
            password=st.text_input("Password",type="password",key="register-password")
            submit=st.form_submit_button("Create account",disabled=not capabilities.get("email_verification"))
        if submit:
            try:
                signed_in(api("POST","/auth/register",json={"email":email,"password":password})); st.rerun()
            except Exception as error: st.error(str(error))
    google_controls(capabilities)


def render():
    capabilities=api("GET","/auth/capabilities",headers={})
    verification=st.query_params.get("verify")
    if verification:
        st.info("Confirm ownership of your email address.")
        if st.button("Confirm email"):
            try:
                api("POST","/auth/verification/confirm",json={"token":verification},headers={})
                st.query_params.clear(); st.success("Email verified. You can sign in now.")
                if st.session_state.token: st.session_state.user=api("GET","/auth/me")
            except Exception as error: st.error(str(error))
    if not st.session_state.token and not st.session_state.guest_id:
        forms(capabilities)
        st.divider()
        if st.button("Start guest session"):
            try:
                data=api("POST","/workspaces",json={"name":"Guest workspace"},headers={})
                st.session_state.guest_id=data["guest_id"]; st.session_state.workspace_id=data["id"]; st.rerun()
            except Exception as error: st.error(str(error))
        st.stop()
    with st.sidebar:
        st.subheader("Account")
        st.write(st.session_state.user["email"] if st.session_state.user else "Guest")
        if st.session_state.user:
            if st.button("Refresh account status"):
                st.session_state.user=api("GET","/auth/me"); st.rerun()
            if st.session_state.user.get("email_verified"):
                with st.expander("Google account"):
                    google_controls(capabilities,link=True)
        else:
            with st.expander("Save your guest workspace"):
                st.caption("Sign in or create an account, verify your email, then claim this session.")
                forms(capabilities)
        if st.button("Logout / end session"):
            try:
                if st.session_state.token: api("POST","/auth/logout")
                elif st.session_state.guest_id: api("POST","/auth/guest/end")
            except Exception as error: st.warning(str(error))
            for key in ["token","refresh_token","user","guest_id","pending_guest","workspace_id","chat_id","dataset_id","google_handoff","google_url"]:
                st.session_state[key]=None
            st.rerun()
    if st.session_state.user and not st.session_state.user.get("email_verified"):
        st.warning("Verify your email before creating or opening workspaces.")
        if st.button("Resend verification email",disabled=not capabilities.get("email_verification")):
            try:
                data=api("POST","/auth/verification/resend",json={"email":st.session_state.user["email"]}); st.success(data["message"])
            except Exception as error: st.error(str(error))
        st.stop()
    if st.session_state.pending_guest:
        if st.button("Claim my guest workspace"):
            try:
                data=api("POST","/workspaces/claim-guest",headers={"Authorization":"Bearer "+st.session_state.token,"X-Guest-Id":st.session_state.pending_guest})
                st.session_state.pending_guest=None; st.success(f"Transferred {data['transferred']} workspace(s)."); st.rerun()
            except Exception as error: st.error(str(error))
