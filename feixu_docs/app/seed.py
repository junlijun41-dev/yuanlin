# -*- coding: utf-8 -*-
"""初始化：管理员账号 + DB11/T712 标准表单模板（六大工艺核心记录表）"""
from .models import db, User, FormTemplate


def _f(key, label, ftype="text", required=False, options=None):
    d = {"key": key, "label": label, "type": ftype, "required": required}
    if options:
        d["options"] = options
    return d

# 通用签字字段
SIGN = [
    _f("constructor", "施工人员"),
    _f("inspector", "检查人/监理"),
    _f("remark", "备注", "textarea"),
]

SEED_TEMPLATES = [
    # ---- 开工报审（通用 C1）----
    dict(code="C1-001", title="工程开工报审表", phase="kaigong", process="tongyong", volume="C1",
         fields=[_f("project_name", "工程名称", required=True), _f("plan_start", "计划开工日期", "date", True),
                 _f("contractor", "施工单位", required=True), _f("manager", "项目负责人"),
                 _f("scope", "施工范围", "textarea"), _f("attach", "附报审材料清单", "textarea")] + SIGN),
    dict(code="C1-005", title="施工现场质量管理检查记录", phase="kaigong", process="tongyong", volume="C1",
         fields=[_f("project_name", "工程名称", required=True), _f("qa_system", "质量管理体系"),
                 _f("staff", "现场管理人员配置"), _f("special_cert", "特种作业证件核查", "textarea")] + SIGN),
    # ---- 树干注射抑絮剂（C2）----
    dict(code="C2-S01", title="树干打孔注射施工记录表", phase="guocheng", process="zhushe", volume="C2",
         fields=[_f("tree_no", "树木编号", required=True), _f("species", "树种"),
                 _f("dbh", "胸径(cm)", required=True), _f("hole_depth", "打孔深度(cm)", required=True),
                 _f("dose", "药剂用量(ml)", required=True), _f("inject_time", "注射时间", "datetime", True),
                 _f("weather", "天气情况"), _f("agent_batch", "药剂批号")] + SIGN),
    dict(code="C2-Y01", title="树干注射隐蔽工程验收记录", phase="guocheng", process="zhushe", volume="C2",
         fields=[_f("tree_no", "树木编号", required=True), _f("hole_check", "打孔质量"),
                 _f("fill_check", "药剂灌注情况"), _f("conclusion", "验收结论", "select", True,
                 ["合格", "不合格", "整改后合格"])] + SIGN),
    # ---- 高压喷水降絮（C3）----
    dict(code="C3-R01", title="高压喷水降絮施工日志", phase="guocheng", process="penshui", volume="C3",
         fields=[_f("date", "日期", "date", True), _f("section", "作业路段/区域", required=True),
                 _f("tree_count", "苗木数量"), _f("duration", "作业时长(h)"),
                 _f("trips", "车次"), _f("leader", "现场负责人")] + SIGN),
    # ---- 树冠修剪（C4）----
    dict(code="C4-S01", title="树木修剪施工记录表", phase="guocheng", process="xiujian", volume="C4",
         fields=[_f("tree_no", "树木编号", required=True), _f("species", "树种"),
                 _f("part", "修剪部位"), _f("ratio", "修剪幅度(%)"),
                 _f("crown_height", "留冠高度(m)"), _f("waste", "废弃物清运量"),
                 _f("high_guard", "高空作业安全监护")] + SIGN),
    # ---- 地面清扫（C3）----
    dict(code="C3-Q01", title="每日清扫保洁施工记录", phase="guocheng", process="qingsao", volume="C3",
         fields=[_f("date", "日期", "date", True), _f("area", "清扫面积(㎡)"),
                 _f("key_area", "重点区域(人行道/绿化带/路口)", "textarea"),
                 _f("collect", "飞絮收集清运量"), _f("disposal", "处置去向")] + SIGN),
    # ---- 雌株高接改造（C5）----
    dict(code="C5-S01", title="雌株嫁接施工记录表", phase="guocheng", process="gaojie", volume="C5",
         fields=[_f("tree_no", "树木编号", required=True), _f("old_species", "原树种"),
                 _f("age", "树龄"), _f("dbh", "胸径(cm)"), _f("graft_pos", "嫁接位置"),
                 _f("graft_way", "嫁接方式"), _f("graft_time", "嫁接时间", "datetime", True),
                 _f("wrap", "包扎工艺"), _f("scion_cert", "接穗检疫证明编号")] + SIGN),
    dict(code="C5-Y01", title="嫁接改造隐蔽工程验收记录", phase="guocheng", process="gaojie", volume="C5",
         fields=[_f("tree_no", "树木编号", required=True), _f("cut_wrap", "切口包扎质量"),
                 _f("moisture", "保湿措施"), _f("conclusion", "验收结论", "select", True,
                 ["合格", "不合格", "整改后合格"])] + SIGN),
    # ---- 老树伐除更新（C6）----
    dict(code="C6-S01", title="老树伐除更新台账", phase="guocheng", process="fachu", volume="C6",
         fields=[_f("tree_no", "树木编号", required=True), _f("species", "树种"),
                 _f("dead_reason", "枯死原因"), _f("fell_way", "伐除方式"),
                 _f("approval_no", "砍伐审批手续编号", required=True),
                 _f("new_seedling", "更新苗木信息"), _f("plant_date", "新植日期", "date")] + SIGN),
    # ---- 过程通用（C7）----
    dict(code="C7-R01", title="每日施工日志", phase="guocheng", process="tongyong", volume="C7",
         fields=[_f("date", "日期", "date", True), _f("process_today", "当日施工工艺"),
                 _f("workers", "施工人数"), _f("machines", "机械投入"),
                 _f("progress", "进度情况"), _f("problems", "问题及整改", "textarea")] + SIGN),
    # ---- 竣工验收（C8）----
    dict(code="C8-V01", title="分项工程质量验收记录", phase="jungong", process="tongyong", volume="C8",
         fields=[_f("subitem", "分项工程名称", required=True), _f("quantity", "工程量"),
                 _f("self_check", "施工单位自评"), _f("conclusion", "验收结论", "select", True,
                 ["合格", "不合格"])] + SIGN),
]


def seed_all():
    if not User.query.filter_by(username="admin").first():
        admin = User(username="admin", name="系统管理员", role="admin")
        admin.set_password("admin123")
        db.session.add(admin)

    for t in SEED_TEMPLATES:
        if not FormTemplate.query.filter_by(code=t["code"]).first():
            tpl = FormTemplate(code=t["code"], title=t["title"], phase=t["phase"],
                               process=t["process"], volume=t["volume"], is_seed=True)
            tpl.fields = t["fields"]
            db.session.add(tpl)
    db.session.commit()
