import streamlit as st

from ui.view_models.labels import format_money
from ui.view_models.post_policy import AdviceReviewView


def render_portfolio(review: AdviceReviewView) -> None:
    """展示预算、报价明细与需要复核的效果估算。"""
    portfolio = review.portfolio
    for column, label, value in zip(st.columns(3), ("预算上限", "建议总价", "区间上限"),
                                    (portfolio.budget_limit, portfolio.total_suggested, portfolio.total_upper)):
        column.metric(label, format_money(value))
    if portfolio.budget_limit > 0:
        ratio = portfolio.total_upper / portfolio.budget_limit
        st.progress(min(max(ratio, 0), 1), text=f"预算占用 {ratio:.1%}")
    st.space("small")
    if portfolio.lines:
        st.dataframe([
            {"达人": item.nickname or item.xhs_id, "形式": item.format_label, "数量": item.quantity,
             "报价区间": f"{format_money(item.unit_price_low)} – {format_money(item.unit_price_high)}",
             "建议单价": item.unit_price_suggested, "建议小计": item.total_suggested,
             "风险": "、".join(item.risk_flags)} for item in portfolio.lines
        ], hide_index=True, width="stretch", row_height=46,
            column_config={"建议单价": st.column_config.NumberColumn(format="¥ %.2f"),
                           "建议小计": st.column_config.NumberColumn(format="¥ %.2f")})
    else:
        st.info("暂无可执行投放项")
    if portfolio.kpis:
        st.markdown("**效果估算**")
        st.dataframe([{"指标": item.label, "目标": item.target, "方案估算": item.estimated, "状态": item.status_label}
                      for item in portfolio.kpis], hide_index=True, width="stretch")
    if portfolio.conditional_names:
        with st.expander(f"待核价达人 · {len(portfolio.conditional_names)}"):
            for name in portfolio.conditional_names:
                st.write(name)
    if portfolio.warnings:
        with st.expander(f"方案待核实 · {len(portfolio.warnings)}"):
            for warning in portfolio.warnings:
                st.write(warning)
