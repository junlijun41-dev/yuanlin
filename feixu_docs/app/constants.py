# -*- coding: utf-8 -*-
"""DB11/T712 飞絮治理施工资料 —— 固定枚举：四阶段、六工艺、C类组卷册"""

# 四大阶段
PHASES = [
    ("kaigong", "开工报审阶段"),
    ("guocheng", "过程管控阶段"),
    ("jungong", "竣工验收阶段"),
    ("zujuan", "组卷移交阶段"),
]

# 六大工艺
PROCESSES = [
    ("tongyong", "通用（不分工艺）"),
    ("zhushe", "树干注射抑絮剂"),
    ("penshui", "高压喷水降絮"),
    ("xiujian", "树冠修剪"),
    ("qingsao", "地面清扫保洁"),
    ("gaojie", "雌株高接改造"),
    ("fachu", "老树伐除更新"),
]

# C类组卷八册（DB11/T712 标准组卷目录）
VOLUMES = [
    ("C1", "第一册 开工报审综合资料"),
    ("C2", "第二册 树干注射抑絮剂专项施工资料"),
    ("C3", "第三册 高压喷水降絮+地面清扫专项资料"),
    ("C4", "第四册 树冠修剪专项施工资料"),
    ("C5", "第五册 雌株高接改造专项施工资料"),
    ("C6", "第六册 老树伐除更新专项施工资料"),
    ("C7", "第七册 过程通用管控资料"),
    ("C8", "第八册 竣工验收全套资料"),
]

PHASE_MAP = dict(PHASES)
PROCESS_MAP = dict(PROCESSES)
VOLUME_MAP = dict(VOLUMES)

# 报验状态机：交底→施工→自检→报验→验收（顺序不可乱）
WORKFLOW_STEPS = [
    ("jiaodi", "技术/安全交底"),
    ("shigong", "施工"),
    ("zijian", "自检"),
    ("baoyan", "报验"),
    ("yanshou", "验收"),
]
WORKFLOW_ORDER = [s[0] for s in WORKFLOW_STEPS]
WORKFLOW_MAP = dict(WORKFLOW_STEPS)
