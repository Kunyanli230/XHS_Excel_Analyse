import streamlit as st

from ui.view_models.workflow import WorkflowView


def render_recovery(view: WorkflowView, service) -> None:
    """在当前任务内恢复报价、建议或文件导出。"""
    if view.replan_available:
        with st.form(f"replan_{view.run_id}", border=False):
            feedback = st.text_area("方案调整", placeholder="填写需要补充或调整的投放要求")
            submitted = st.form_submit_button("调整方案", type="primary", width="stretch")
        if submitted:
            if feedback.strip():
                with st.spinner("正在调整方案"):
                    service.replan(feedback)
                st.rerun()
            st.error("请填写调整意见")
    if view.retry_available and st.button("重试", key=f"retry_{view.run_id}"):
        with st.spinner("正在重试"):
            service.retry()
        st.rerun()
