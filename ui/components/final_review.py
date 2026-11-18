import streamlit as st

from ui.view_models.labels import format_money
from ui.view_models.post_policy import AdviceReviewView, FinalReviewDecision


def render_final_review(review: AdviceReviewView, run_id: str, *, disabled: bool) -> FinalReviewDecision | None:
    """展示内容建议并提交当前版本的最终审核。"""
    if not review.recommendations:
        st.info("暂无内容建议")
        return None
    for index, item in enumerate(review.recommendations):
        with st.container(border=True):
            name_column, price_column = st.columns([3, 2])
            name_column.markdown(f"**{item.nickname or item.xhs_id}**")
            price_column.markdown(f"{item.format_label} × {item.quantity} · {format_money(item.total_price)}")
            st.caption(" · ".join(value for value in (item.tag, item.angle, item.sub_angle) if value))
            if item.sentence:
                st.write(item.sentence)
            if item.details:
                st.write(item.details)
            if item.advice_status == "failed":
                st.warning("内容建议生成失败")
            if item.warnings or item.remarks:
                with st.expander("待核实与备注", key=f"recommendation_risks_{run_id}_{index}"):
                    for warning in (*item.warnings, *item.remarks):
                        st.write(warning)
    if review.unverified_checks:
        with st.expander(f"人工核对 · {len(review.unverified_checks)}"):
            for check in review.unverified_checks:
                st.write(check)
    if not review.can_approve:
        return None
    key = f"final_{run_id}_{review.portfolio.revision}"
    with st.form(f"{key}_form", border=False):
        feedback = st.text_area("修改意见", key=f"{key}_feedback", placeholder="填写报价或投放组合的调整意见", disabled=disabled)
        approve_column, reprice_column = st.columns(2)
        approved = approve_column.form_submit_button("审核通过并导出", key=f"{key}_approve", type="primary",
                                                     disabled=disabled, width="stretch")
        repriced = reprice_column.form_submit_button("打回重定价", key=f"{key}_reprice", disabled=disabled, width="stretch")
    if approved:
        return FinalReviewDecision("approve", review.portfolio.revision, expected_run_id=run_id)
    if repriced:
        if feedback.strip():
            return FinalReviewDecision("reprice", review.portfolio.revision, feedback.strip(), expected_run_id=run_id)
        st.error("请填写修改意见")
    return None
