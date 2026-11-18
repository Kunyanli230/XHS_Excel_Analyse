from copy import deepcopy
from pathlib import Path
from uuid import uuid4

import streamlit as st

from agent.export_table import export_recommendations
from ui.adapters.post_policy_workflow import PostPolicyWorkflowAdapter
from ui.adapters.run_upload_store import RunUploadStore
from ui.adapters.streamlit_run_store import StreamlitRunStore
from ui.pages.workflow_page import render
from ui.services.workflow_service import WorkflowService
from ui.styles.theme import apply_theme
from ui.tests.fixtures import make_context, sample_state


def policy_state():
    """提供与实际中断合同一致的合成策略。"""
    return {"type": "policy_review", "policy": {
        "name": "屿光精华达人筛选策略", "rationale": "优先年轻女性受众，以互动成本与曝光表现比较候选达人。",
        "criteria": [
            {"field": "main_format", "operator": "not_contains", "value": "vlog", "hard": True, "weight": 0, "reason": "排除纯生活记录账号"},
            {"field": "ratio_female", "operator": "maximize", "value": None, "hard": False, "weight": .4, "reason": "目标人群为女性"},
            {"field": "cpe", "operator": "minimize", "value": None, "hard": False, "weight": .6, "reason": "控制互动成本"},
        ], "manual_checks": ["核对近期品牌合作记录"],
    }}


class PreviewWorkflow:
    """仅供离线验收使用的工作流边界替身。"""

    def start(self, run_id, files):
        """模拟上传后等待策略审核。"""
        context = make_context(files.run_dir, state={"workflow_status": "awaiting_policy_review"},
                               files=files, interrupt_type="policy_review", interrupt_id="policy-1",
                               interrupt_payload=policy_state(), run_id=run_id)
        return context

    def resume_policy(self, context, decision):
        """模拟策略修改与批准后的下游结果。"""
        if decision.action == "revise":
            context.latest_state["policy_revision_count"] = context.latest_state.get("policy_revision_count", 0) + 1
            context.interrupt_id = uuid4().hex
            context.interrupt_payload["policy"]["name"] = "屿光精华达人筛选策略 · 修订版"
            return context
        context.latest_state = sample_state()
        context.interrupt_type, context.interrupt_payload, context.interrupt_id = None, {}, None
        generate_preview(context)
        return context


def generate_preview(context):
    """在当前合成任务目录导出可验证的预览工作簿。"""
    if not context.latest_state.get("recommendations"):
        return
    path = context.files.run_dir / f"preview_{uuid4().hex}.xlsx"
    export_recommendations(context.latest_state["recommendations"], path, review_status="pending", preview=True)
    context.latest_state["advice_preview_path"] = str(path)


def portfolio_factory(_client):
    """隔离模型服务以验证重定价交互。"""
    def reprice(state):
        """返回第二轮合成报价。"""
        plan = deepcopy(state.get("portfolio_plan") or sample_state()["portfolio_plan"])
        plan["revision"] += 1
        for line in plan["lines"]:
            for key in ("unit_price_low", "unit_price_suggested", "unit_price_high", "line_cost_suggested"):
                line[key] *= .9
        plan["budget"]["total_suggested"] *= .9
        plan["budget"]["total_upper"] *= .9
        return {"portfolio_plan": plan, "portfolio_error": None, "workflow_status": "portfolio_ready"}
    return reprice


def advice_factory(_client, *, output_dir):
    """在合成报价基础上生成独立建议与预览。"""
    def advise(state):
        """保持报价与建议中的金额同步。"""
        rows = sample_state()["recommendations"]
        line = state["portfolio_plan"]["lines"][0]
        rows[0].update(unit_price=line["unit_price_suggested"], total_price=line["line_cost_suggested"])
        path = output_dir / f"preview_{uuid4().hex}.xlsx"
        export_recommendations(rows, path, review_status="pending", preview=True)
        return {"recommendations": rows, "workflow_status": "advice_ready", "advice_preview_path": str(path)}
    return advise


def preview_service():
    """使用与生产页面相同的服务及组件装配离线验收。"""
    store = StreamlitRunStore(st.session_state)
    root = Path(__file__).parent / ".artifacts"
    scenario = st.query_params.get("scenario", "review")
    if "_preview_initialized" not in st.session_state:
        st.session_state["_preview_initialized"] = True
        if scenario != "upload":
            context = make_context(root / uuid4().hex)
            if scenario == "no_candidates":
                context.latest_state.update(workflow_status="portfolio_no_candidates", recommendations=[])
                context.latest_state["portfolio_plan"]["lines"] = []
            elif scenario == "failed_advice":
                context.latest_state["workflow_status"] = "advice_needs_review"
                context.latest_state["recommendations"][0].update(advice_status="failed", details="", advice_error="validation failed")
            elif scenario == "empty_results":
                context.latest_state["audited_talents"] = []
            generate_preview(context)
            store.save(context)
    return WorkflowService(RunUploadStore(root), PreviewWorkflow(), store,
                           post_policy=PostPolicyWorkflowAdapter(portfolio_node_factory=portfolio_factory,
                                                                 advice_node_factory=advice_factory))


st.set_page_config(page_title="达人投放分析", layout="wide", initial_sidebar_state="collapsed")
apply_theme()
render(preview_service())
