from __future__ import annotations

import streamlit as st

from ui.view_models.post_policy import AdviceReviewView


def render_advice_review(review: AdviceReviewView) -> None:
    results_tab, portfolio_tab, approval_tab = st.tabs(["达人结果", "投放方案", "最终审核"])
    with results_tab:
        _render_candidates(review)
    with portfolio_tab:
        _render_portfolio(review)
    with approval_tab:
        _render_recommendations(review)


def _render_candidates(review: AdviceReviewView) -> None:
    summary = review.audit
    columns = st.columns(4)
    columns[0].metric("进入流程", summary.input_count)
    columns[1].metric("推荐", summary.recommended_count)
    columns[2].metric("不推荐", summary.rejected_count)
    columns[3].metric("待处理", summary.pending_count)
    st.dataframe(
        [
            {
                "达人": item.nickname or item.xhs_id,
                "档位": item.band,
                "评分": item.score,
                "结论": _stance_label(item.stance),
                "推荐标签": item.tag,
                "推荐理由": item.sentence,
                "审核": _audit_label(item.audit_status),
                "风险": "数据不全" if item.data_incomplete else "",
            }
            for item in review.candidates
        ],
        hide_index=True,
        width="stretch",
    )


def _render_portfolio(review: AdviceReviewView) -> None:
    portfolio = review.portfolio
    columns = st.columns(3)
    columns[0].metric("预算上限", _money(portfolio.budget_limit))
    columns[1].metric("建议总价", _money(portfolio.total_suggested))
    columns[2].metric("区间上限", _money(portfolio.total_upper))
    st.dataframe(
        [
            {
                "达人": item.nickname or item.xhs_id,
                "形式": item.format_label,
                "数量": item.quantity,
                "价格区间": f"{_money(item.unit_price_low)} – {_money(item.unit_price_high)}",
                "建议单价": _money(item.unit_price_suggested),
                "建议小计": _money(item.total_suggested),
                "风险": "、".join(item.risk_flags),
            }
            for item in portfolio.lines
        ],
        hide_index=True,
        width="stretch",
    )
    for warning in portfolio.warnings:
        st.caption(warning)


def _render_recommendations(review: AdviceReviewView) -> None:
    if review.preview_error:
        st.warning(review.preview_error)
    st.dataframe(
        [
            {
                "达人": item.nickname or item.xhs_id,
                "形式": item.format_label,
                "数量": item.quantity,
                "单价": _money(item.unit_price),
                "小计": _money(item.total_price),
                "推荐标签": item.tag,
                "推荐理由": item.sentence,
                "内容角度": item.angle,
                "子角度": item.sub_angle,
                "内容建议": item.details,
                "待核实事项": "、".join(item.warnings),
                "状态": "已生成" if item.advice_status == "generated" else "待补充",
            }
            for item in review.recommendations
        ],
        hide_index=True,
        width="stretch",
    )


def _money(value: float) -> str:
    return f"¥{value:,.2f}"


def _stance_label(value: str) -> str:
    return {"recommend": "推荐", "not_recommend": "不推荐"}.get(value, value)


def _audit_label(value: str) -> str:
    return {
        "passed": "通过",
        "skipped_clear_band": "明确档",
        "needs_resolution": "待处理",
        "execution_error": "执行异常",
    }.get(value, value)
