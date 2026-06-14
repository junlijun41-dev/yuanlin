# -*- coding: utf-8 -*-
"""DeepSeek 接入：规程问答 / 智能填表 / 自动写文档 / 缺项避坑检查。
Key 读取顺序：环境变量 DEEPSEEK_API_KEY > instance/ai_key.txt。
"""
import json
import os

import requests

from .constants import PROCESS_MAP

BASE_URL = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
TIMEOUT = 120

SYSTEM = (
    "你是北京园林绿化工程资料专家，精通《DB11/T712-2020 园林绿化工程资料管理规程》，"
    "熟悉杨柳飞絮综合治理六大工艺：树干注射抑絮剂、高压喷水降絮、树冠修剪、地面清扫、"
    "雌株高接改造、老树伐除更新。报验顺序固定为：交底→施工→自检→报验→验收。"
    "回答务必专业、简洁、可直接用于施工资料归档。"
)


class AIError(Exception):
    pass


def _key():
    k = os.environ.get("DEEPSEEK_API_KEY")
    if k:
        return k.strip().lstrip("﻿")
    from flask import current_app
    path = os.path.join(os.path.dirname(current_app.config["UPLOAD_DIR"]), "ai_key.txt")
    if os.path.exists(path):
        with open(path, encoding="utf-8-sig") as f:  # utf-8-sig 自动剥离 BOM
            return f.read().strip().lstrip("﻿")
    raise AIError("未配置 DeepSeek API Key（设置环境变量 DEEPSEEK_API_KEY 或 instance/ai_key.txt）")


def chat(messages, model="deepseek-chat", json_mode=False, temperature=0.4, max_tokens=2000):
    """调用 DeepSeek，返回 (文本, usage字典)。"""
    payload = {"model": model, "messages": messages,
               "temperature": temperature, "max_tokens": max_tokens}
    if json_mode:
        payload["response_format"] = {"type": "json_object"}
    try:
        resp = requests.post(
            BASE_URL.rstrip("/") + "/chat/completions",
            headers={"Authorization": "Bearer " + _key(), "Content-Type": "application/json"},
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            timeout=TIMEOUT,
        )
    except requests.RequestException as e:
        raise AIError("网络请求失败：%s" % e)
    if resp.status_code != 200:
        raise AIError("DeepSeek 返回 %d：%s" % (resp.status_code, resp.text[:300]))
    data = resp.json()
    return data["choices"][0]["message"]["content"], data.get("usage", {})


# ---------------- 四大功能 ----------------

def ask_regulation(question, history=None):
    """规程问答助手。"""
    msgs = [{"role": "system", "content": SYSTEM}]
    if history:
        msgs.extend(history)
    msgs.append({"role": "user", "content": question})
    return chat(msgs, model="deepseek-chat")


def fill_form(fields, raw_text):
    """智能填表：把现场口述/粘贴文本，拆成表单字段值。
    fields: [{key,label,type,...}]；返回 (dict, usage)。
    """
    field_desc = "\n".join("- %s（key=%s，类型=%s）" % (f["label"], f["key"], f.get("type", "text"))
                           for f in fields)
    keys = [f["key"] for f in fields]
    prompt = (
        "下面是一张施工资料表的字段，请根据【现场描述】抽取对应内容，"
        "只输出 JSON 对象，键必须是给定的字段 key（%s），无法确定的留空字符串，不要编造。\n\n"
        "【表单字段】\n%s\n\n【现场描述】\n%s" % (keys, field_desc, raw_text)
    )
    msgs = [{"role": "system", "content": SYSTEM + " 你只输出严格的 JSON，不加解释。"},
            {"role": "user", "content": prompt}]
    text, usage = chat(msgs, model="deepseek-chat", json_mode=True, temperature=0.1)
    try:
        result = json.loads(text)
    except (ValueError, TypeError):
        raise AIError("AI 返回的不是有效 JSON：" + text[:200])
    # 只保留合法字段
    return {k: str(result.get(k, "")) for k in keys}, usage


DOC_TYPES = {
    "fangan": "杨柳飞絮综合治理专项施工方案（含六大工艺施工流程、安全措施、质量标准、工期计划）",
    "rizhi": "施工日志（当日施工工艺、人数、机械、进度、问题整改）",
    "zongjie": "工程施工总结（全过程施工、质量、安全、养护总结）",
    "ziping": "工程质量自评报告",
}


def generate_document(doc_type, project_name, context):
    """自动写文档：方案/日志/总结/自评。"""
    desc = DOC_TYPES.get(doc_type, doc_type)
    prompt = (
        "请为工程【%s】撰写一份《%s》，要求符合 DB11/T712 与北京园林质监归档要求，"
        "结构清晰、分条目、可直接作为施工资料初稿。\n\n补充信息：\n%s"
        % (project_name, desc, context or "（无额外信息，按通用飞絮治理工程撰写）")
    )
    msgs = [{"role": "system", "content": SYSTEM},
            {"role": "user", "content": prompt}]
    return chat(msgs, model="deepseek-chat", max_tokens=4000)


def check_missing(project_name, records_summary):
    """缺项/质监避坑检查：扫描已填资料，对照规程指出问题。records_summary 为文本概要。"""
    prompt = (
        "下面是工程【%s】当前已填报的施工资料清单（按工艺/状态）。请对照 DB11/T712 与北京质监"
        "必查项，指出：1) 缺失的关键资料；2) 报验顺序问题；3) 质监避坑红灯"
        "（如抑絮剂药剂检测/环保报告、隐蔽验收、特种作业证有效期、老树伐除审批手续、"
        "台账连续性等）。按【🔴严重/🟡提醒/✅正常】分级，条目化输出。\n\n"
        "【已填资料】\n%s" % (project_name, records_summary)
    )
    msgs = [{"role": "system", "content": SYSTEM},
            {"role": "user", "content": prompt}]
    return chat(msgs, model="deepseek-reasoner", max_tokens=3000, temperature=0.2)
