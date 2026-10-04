import json
import pandas as pd
import streamlit as st
from frontend.client import api,download


def render_result(record,show_plan=True):
    if record.get("clarification"):
        st.info(record["clarification"]); return
    result=record.get("result",{})
    if record.get("narrative"): st.write(record["narrative"])
    if "data" in result:
        st.caption(f"{result.get('rows_considered',0)} rows considered · {result.get('scope','')} · {result.get('result_rows',0)} result rows")
        if result.get("truncated"): st.info("The displayed result is truncated; calculations used the full filtered dataset.")
        frame=pd.DataFrame(result["data"],columns=result.get("columns"))
        st.dataframe(frame,use_container_width=True)
        chart=result.get("chart")
        if chart and not frame.empty:
            x,y=chart["x"],chart.get("y")
            try:
                if chart["type"]=="bar": st.bar_chart(frame,x=x,y=y)
                elif chart["type"]=="line": st.line_chart(frame,x=x,y=y)
                elif chart["type"]=="scatter": st.scatter_chart(frame,x=x,y=y)
                elif chart["type"]=="histogram":
                    import altair as alt
                    st.altair_chart(alt.Chart(frame).mark_bar().encode(x=alt.X(x+":Q",bin=True),y="count()"),use_container_width=True)
            except Exception: st.info("These values cannot be plotted with that chart type. Try another chart.")
        if result.get("notes"): st.caption(result["notes"])
    if record.get("plan") and show_plan:
        with st.expander("Reproducible analysis plan and source"):
            st.json({"dataset_id":record.get("dataset_id"),"version":record.get("version"),"plan":record["plan"]})


def render(workspace):
    st.subheader("Data Analysis")
    st.caption("CSV and XLSX datasets are analyzed using deterministic calculations, separately from document retrieval.")
    uploaded=st.file_uploader("Upload a dataset",type=["csv","xlsx"],key="dataset-upload")
    if uploaded and st.button("Upload dataset"):
        try:
            result=api("POST",f"/workspaces/{workspace['id']}/datasets",files={"file":(uploaded.name,uploaded.getvalue())})
            st.session_state.dataset_id=result["id"]; st.rerun()
        except Exception as error: st.error(str(error))
    if st.button("Refresh datasets"): st.rerun()
    datasets=api("GET",f"/workspaces/{workspace['id']}/datasets")
    if not datasets: st.info("Upload a dataset to begin."); return
    labels={item["id"]:f"{item['filename']} — {item['status']}" for item in datasets}
    preferred=st.session_state.dataset_id if st.session_state.dataset_id in labels else next(iter(labels))
    selected=st.selectbox("Dataset",list(labels),format_func=labels.get,index=list(labels).index(preferred),key="dataset-select-"+workspace["id"])
    st.session_state.dataset_id=selected
    dataset=api("GET",f"/datasets/{selected}")
    if dataset.get("error"): st.warning(dataset["error"])
    if dataset["status"]=="failed" and st.button("Retry dataset"):
        api("POST",f"/datasets/{selected}/retry"); st.rerun()
    with st.expander("Dataset management"):
        if st.button("Prepare dataset download"):
            try: st.download_button("Download original dataset",download(f"/datasets/{selected}/download"),file_name=dataset["filename"])
            except Exception as error: st.error(str(error))
        confirmed=st.checkbox("Delete this dataset and all its analysis results",key="delete-confirm-"+selected)
        if st.button("Delete dataset",disabled=not confirmed):
            api("DELETE",f"/datasets/{selected}"); st.session_state.dataset_id=None; st.rerun()
    if dataset["status"]!="ready":
        st.info("Waiting for background processing. Start '.venv/bin/python -m backend.worker' if no worker is running."); return
    sheets=dataset["profile"]["sheets"]
    sheet=st.selectbox("Worksheet",list(sheets),key="sheet-"+selected)
    profile=sheets[sheet]
    mapping={column["id"]:f"{column['name']} ({column['id']})" for column in profile["columns"]}
    columns=list(mapping)
    a,b,c=st.columns(3)
    a.metric("Rows",profile["rows"]); b.metric("Columns",len(columns)); c.metric("Duplicate rows",profile["duplicate_rows"])
    overview,explore,questions,history=st.tabs(["Overview","Explore & charts","Ask your data","Analysis history"])
    with overview:
        st.write("Columns, data types and missing values")
        st.dataframe(pd.DataFrame(profile["columns"]),use_container_width=True)
        st.write("Preview — first 20 rows")
        st.dataframe(pd.DataFrame(profile["preview"]).rename(columns={column["id"]:column["name"] for column in profile["columns"]}),use_container_width=True)
        st.write("Numeric descriptive statistics — full dataset")
        st.dataframe(pd.DataFrame(profile["statistics"]),use_container_width=True)
        st.caption(dataset["profile"]["formula_policy"])
        if st.button("Generate AI dataset summary"):
            try:
                with st.spinner("Summarizing computed statistics…"): record=api("POST",f"/datasets/{selected}/summary")
                render_result(record)
            except Exception as error: st.error(str(error))
    with explore:
        operation=st.selectbox("Analysis",["preview","describe","missing","duplicates","aggregate","trend","correlation","anomalies"],key="operation-"+selected)
        plan={"sheet":sheet,"operation":operation,"limit":100}
        chosen=st.multiselect("Columns (optional)",columns,format_func=mapping.get,key="analysis-columns-"+selected)
        plan["columns"]=chosen
        with st.expander("Filter rows"):
            filter_column=st.selectbox("Filter column",[None]+columns,format_func=lambda key:mapping.get(key,"No filter"),key="filter-column-"+selected)
            operator=st.selectbox("Condition",["eq","ne","gt","ge","lt","le","contains","is_null","not_null","in"],key="filter-op-"+selected)
            value=st.text_input("Value (comma-separated for 'in')",key="filter-value-"+selected)
            if filter_column:
                dtype=next(column["dtype"] for column in profile["columns"] if column["id"]==filter_column)
                numeric="int" in dtype.lower() or "float" in dtype.lower()
                try:
                    scalar=lambda item:float(item) if numeric and operator!="contains" else item
                    parsed=[scalar(item.strip()) for item in value.split(",")] if operator=="in" else (None if operator in {"is_null","not_null"} else scalar(value))
                    plan["filters"]=[{"column":filter_column,"operator":operator,"value":parsed}]
                except ValueError:
                    st.warning("Enter a numeric filter value for this column.")
                    plan["filters"]=[{"column":filter_column,"operator":operator,"value":value}]
        if operation in {"aggregate","trend"}:
            plan["group_by"]=st.multiselect("Group by",columns,format_func=mapping.get,key="group-"+selected)
            function=st.selectbox("Measure",["sum","mean","min","max","count","median"],key="function-"+selected)
            column=st.selectbox("Measure column",([None]+columns) if function=="count" else columns,
                                format_func=lambda key:mapping.get(key,"All rows"),key="measure-column-"+selected)
            plan["measures"]=[{"column":column,"function":function}]
            if operation=="trend":
                plan["date_column"]=st.selectbox("Date column",columns,format_func=mapping.get,key="date-column-"+selected)
                plan["interval"]=st.selectbox("Time interval",["day","week","month","year"],key="interval-"+selected)
        chart=st.selectbox("Chart",["none","bar","line","scatter","histogram"],key="chart-"+selected)
        plan["chart"]=chart
        if st.button("Run analysis"):
            try:
                record=api("POST",f"/datasets/{selected}/analyze",json=plan)
                st.session_state["analysis-"+selected]=record
            except Exception as error: st.error(str(error))
        if st.session_state.get("analysis-"+selected): render_result(st.session_state["analysis-"+selected])
    with questions:
        with st.form("data-question-"+selected):
            question=st.text_input("Ask a question",placeholder="What is total sales by region?")
            submitted=st.form_submit_button("Analyze question")
        if submitted:
            try:
                with st.spinner("Planning and calculating…"):
                    record=api("POST",f"/datasets/{selected}/ask",json={"question":question,"sheet":sheet})
                st.session_state["answer-"+selected]=record
            except Exception as error: st.error(str(error))
        if st.session_state.get("answer-"+selected): render_result(st.session_state["answer-"+selected])
    with history:
        records=api("GET",f"/datasets/{selected}/history")["history"]
        for record in records:
            with st.expander(record.get("question") or record["plan"]["operation"]):
                render_result(record,show_plan=False)
                st.json({"version":record.get("version"),"plan":record["plan"]})
