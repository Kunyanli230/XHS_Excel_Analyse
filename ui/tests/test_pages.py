from pathlib import Path

from streamlit.testing.v1 import AppTest


PREVIEW = Path(__file__).with_name("preview_app.py")


def load_page(scenario="review"):
    """运行真实页面组件及离线工作流。"""
    app = AppTest.from_file(str(PREVIEW), default_timeout=15)
    app.query_params["scenario"] = scenario
    return app.run()


def button(app, label):
    """按用户可见名称定位操作。"""
    return next(item for item in app.button if item.label == label)


def test_review_page_renders_three_tabs_without_exceptions():
    """结果、投放方案与审核页均能完整渲染。"""
    app = load_page()
    assert not app.exception
    assert [item.label for item in app.tabs] == ["达人结果", "投放方案", "最终审核"]
    assert len(app.metric) == 7
    assert list(app.dataframe[0].value["结论"]) == ["推荐", "不推荐", "待处理"]


def test_search_empty_state_is_recoverable():
    """空搜索结果可通过清除查询恢复。"""
    app = load_page()
    app.text_input[0].input("不存在的达人").run()
    assert "暂无匹配达人" in [item.value for item in app.info]
    app.text_input[0].input("").run()
    assert len(app.dataframe[0].value) == 3
    assert not app.exception


def test_conclusion_filter_keeps_held_accounts_out_of_recommendations():
    """推荐筛选不会混入待处理的达人。"""
    app = load_page()
    app.get("button_group")[0].set_value("推荐").run()
    assert list(app.dataframe[0].value["达人"]) == ["桃桃吃梨"]
    app.get("button_group")[0].set_value("待处理").run()
    assert list(app.dataframe[0].value["达人"]) == ["山茶开在冬天"]


def test_repricing_requires_feedback_then_displays_new_revision():
    """空意见不会重定价，有效意见生成新一版。"""
    app = load_page()
    button(app, "打回重定价").click().run()
    assert "请填写修改意见" in [item.value for item in app.error]
    app.text_area[0].input("报价降低一成")
    button(app, "打回重定价").click().run()
    assert not app.exception
    context = app.session_state["_xhs_workflow_run"]
    assert context.latest_state["portfolio_plan"]["revision"] == 2
    assert context.latest_state["recommendations"][0]["unit_price"] == 8550


def test_approval_keeps_results_and_removes_duplicate_approval():
    """批准成功后保留结果并移除审批按钮。"""
    app = load_page()
    button(app, "审核通过并导出").click().run()
    assert not app.exception
    assert app.session_state["_xhs_workflow_run"].latest_state["workflow_status"] == "export_complete"
    assert len(app.tabs) == 3
    assert not any(item.label == "审核通过并导出" for item in app.button)


def test_failed_advice_remains_visible_for_human_review():
    """建议生成失败作为业务风险保留在审核页。"""
    app = load_page("failed_advice")
    assert not app.exception
    assert "内容建议生成失败" in [item.value for item in app.warning]


def test_no_portfolio_has_results_and_recovery_controls():
    """空方案仍保留结果与调整入口。"""
    app = load_page("no_candidates")
    assert not app.exception
    assert button(app, "调整方案")
    assert not any(item.label == "重试" for item in app.button)
    assert not any(item.label == "审核通过并导出" for item in app.button)


def test_reset_returns_to_clean_upload_page():
    """开始新任务清除结果和旧文件引用。"""
    app = load_page()
    button(app, "开始新任务").click().run()
    assert not app.exception
    assert not app.tabs
    assert button(app, "开始分析").disabled
