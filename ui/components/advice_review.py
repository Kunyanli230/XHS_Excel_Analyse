import streamlit as st

from ui.components.candidate_results import render_candidates
from ui.components.deliverables import render_download
from ui.components.final_review import render_final_review
from ui.components.portfolio import render_portfolio
from ui.view_models.workflow import RunPhase, WorkflowView


def render_advice_review(view: WorkflowView, service) -> None:
    """组合独立的结果、方案、审核与下载组件。"""
    review = view.advice_review
    if review is None:
        return
    scope = f"{view.run_id}_{review.portfolio.revision}"
    if view.phase is RunPhase.COMPLETED:
        version_column, download_column = st.columns([3, 1])
        version_column.caption(f"已审核 · 第 {review.portfolio.revision} 版")
        with download_column:
            render_download(service, "final", scope)
    results_tab, portfolio_tab, approval_tab = st.tabs(["达人结果", "投放方案", "最终审核"])
    with results_tab:
        render_candidates(review, str(view.run_id))
    with portfolio_tab:
        render_portfolio(review)
    with approval_tab:
        if review.preview_available and view.phase is not RunPhase.COMPLETED:
            _, download_column = st.columns([3, 1])
            with download_column:
                render_download(service, "preview", scope)
        if review.preview_error:
            st.warning("预览表生成失败")
        decision = render_final_review(review, str(view.run_id), disabled=view.busy)
        if decision is not None:
            with st.spinner("正在导出" if decision.action == "approve" else "正在重新定价"):
                service.decide_final(decision)
            st.rerun()
