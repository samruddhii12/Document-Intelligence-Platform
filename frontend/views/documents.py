import streamlit as st
from frontend.client import api,download


def render(workspace):
    left,right=st.columns([1,2])
    with left:
        st.subheader("Documents")
        upload=st.file_uploader("PDF, DOCX, Markdown or text",type=["pdf","docx","md","txt"])
        if upload and st.button("Upload & index"):
            try:
                api("POST",f"/workspaces/{workspace['id']}/documents",files={"file":(upload.name,upload.getvalue())})
                st.success("Upload stored securely. The worker will index it."); st.rerun()
            except Exception as error: st.error(str(error))
        if st.button("Refresh processing status"): st.rerun()
        for document in workspace["documents"]:
            did=document["id"]
            with st.expander(f"{document['filename']} — {document['status']}"):
                if document.get("error"): st.warning(document["error"])
                if document["status"] in {"queued","processing"}: st.caption("Processing in the background. Refresh to check progress.")
                if document["status"]=="failed" and st.button("Retry",key="retry-"+did):
                    try: api("POST",f"/documents/{did}/retry"); st.rerun()
                    except Exception as error: st.error(str(error))
                if st.button("Summarize",key="summary-"+did,disabled=document["status"]!="indexed"):
                    try:
                        with st.spinner("Summarizing all document sections…"):
                            st.write(api("POST",f"/documents/{did}/summary")["summary"])
                    except Exception as error: st.error(str(error))
                if st.button("Suggested questions",key="questions-"+did,disabled=document["status"]!="indexed"):
                    try:
                        for question in api("GET",f"/documents/{did}/suggested-questions")["questions"]: st.write("• "+question)
                    except Exception as error: st.error(str(error))
                if st.button("Prepare original download",key="download-"+did):
                    try: st.download_button("Download original",download(f"/documents/{did}/download"),file_name=document["filename"],key="save-"+did)
                    except Exception as error: st.error(str(error))
                confirm=st.checkbox("Delete this document and conversations citing it",key="confirm-delete-"+did)
                if st.button("Delete document",key="delete-"+did,disabled=not confirm):
                    try:
                        api("DELETE",f"/documents/{did}"); st.session_state.chat_id=None; st.rerun()
                    except Exception as error: st.error(str(error))
        indexed=[document for document in workspace["documents"] if document["status"]=="indexed"]
        labels={document["id"]:document["filename"] for document in indexed}
        selected=st.multiselect("Compare documents",list(labels),format_func=labels.get)
        if st.button("Compare selected",disabled=len(selected)<2):
            try:
                with st.spinner("Comparing documents…"):
                    st.write(api("POST",f"/workspaces/{workspace['id']}/compare",json=selected)["comparison"])
            except Exception as error: st.error(str(error))
    with right:
        st.subheader("Document chat")
        labels={chat["id"]:f"{chat['title']} · {chat['id'][:6]}" for chat in workspace["chats"]}
        widget_key="previous-"+workspace["id"]
        if st.session_state.get("pending_chat_selection") in labels:
            st.session_state[widget_key]=st.session_state.pending_chat_selection
            st.session_state.pending_chat_selection=None
        selected=st.selectbox("Previous chats",[None]+list(labels),format_func=lambda key:labels.get(key,"New chat"),key=widget_key)
        if selected: st.session_state.chat_id=selected
        if st.button("Start new chat"):
            try:
                st.session_state.chat_id=api("POST",f"/workspaces/{workspace['id']}/chats")["id"]
                st.session_state.pending_chat_selection=st.session_state.chat_id; st.rerun()
            except Exception as error: st.error(str(error))
        if st.session_state.chat_id:
            try:
                history=api("GET",f"/chats/{st.session_state.chat_id}/history")["history"]
                for message in history:
                    with st.chat_message(message["role"]):
                        st.write(message["content"])
                        if message["role"]=="assistant" and message.get("sources"):
                            with st.expander("Sources"):
                                for source in message["sources"]:
                                    location=source.get("location") or {}
                                    details=source.get("section_title") or ""
                                    if source.get("page_number"): details+=f" · page {source['page_number']}"
                                    if location.get("line_start"): details+=f" · lines {location['line_start']}–{location['line_end']}"
                                    st.caption(f"{source['file_name']} · {details} · chunk {source['chunk_index']}")
            except Exception as error: st.error(str(error)); return
            question=st.chat_input("Ask about indexed documents…",disabled=not indexed)
            if question:
                try:
                    with st.spinner("Retrieving evidence and answering…"):
                        api("POST",f"/chats/{st.session_state.chat_id}/ask",json={"query":question})
                    st.rerun()
                except Exception as error: st.error(str(error))
