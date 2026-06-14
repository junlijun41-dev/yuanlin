# -*- coding: utf-8 -*-
from flask import (Blueprint, jsonify, redirect, render_template, request,
                   url_for)
from flask_login import login_required

from . import ai
from .ai import DOC_TYPES
from .constants import WORKFLOW_MAP
from .models import FormRecord, FormTemplate, Project

ai_bp = Blueprint("ai", __name__, url_prefix="/ai")


@ai_bp.route("/")
@login_required
def home():
    projects = Project.query.order_by(Project.created_at.desc()).all()
    return render_template("ai_home.html", doc_types=DOC_TYPES, projects=projects)


@ai_bp.route("/ask", methods=["POST"])
@login_required
def ask():
    """规程问答（ajax）。"""
    q = (request.json or {}).get("question", "").strip()
    history = (request.json or {}).get("history", [])
    if not q:
        return jsonify(error="问题不能为空"), 400
    try:
        answer, usage = ai.ask_regulation(q, history=history[-6:])
        return jsonify(answer=answer, usage=usage)
    except ai.AIError as e:
        return jsonify(error=str(e)), 502


@ai_bp.route("/fill/<int:tid>", methods=["POST"])
@login_required
def fill(tid):
    """智能填表（ajax）：返回字段值字典。"""
    tpl = FormTemplate.query.get_or_404(tid)
    raw = (request.json or {}).get("raw_text", "").strip()
    if not raw:
        return jsonify(error="请先输入现场描述"), 400
    try:
        values, usage = ai.fill_form(tpl.fields, raw)
        return jsonify(values=values, usage=usage)
    except ai.AIError as e:
        return jsonify(error=str(e)), 502


@ai_bp.route("/doc", methods=["POST"])
@login_required
def doc():
    """自动写文档（ajax）。"""
    data = request.json or {}
    dtype = data.get("doc_type")
    pname = data.get("project_name", "杨柳飞絮综合治理工程")
    context = data.get("context", "")
    if dtype not in DOC_TYPES:
        return jsonify(error="未知文档类型"), 400
    try:
        text, usage = ai.generate_document(dtype, pname, context)
        return jsonify(text=text, usage=usage)
    except ai.AIError as e:
        return jsonify(error=str(e)), 502


@ai_bp.route("/check/<int:pid>", methods=["GET", "POST"])
@login_required
def check(pid):
    """缺项/质监避坑检查。"""
    p = Project.query.get_or_404(pid)
    records = FormRecord.query.filter_by(project_id=pid).all()
    if not records:
        summary = "（该项目暂无任何填报记录）"
    else:
        lines = []
        for r in records:
            t = r.template
            lines.append("- [%s/%s] %s（编号%s，报验状态：%s）" % (
                t.volume, t.title, r.title, t.code or "",
                WORKFLOW_MAP.get(r.workflow_step, r.workflow_step)))
        summary = "\n".join(lines)
    report, usage, err = None, None, None
    if request.method == "POST":
        try:
            report, usage = ai.check_missing(p.name, summary)
        except ai.AIError as e:
            err = str(e)
    return render_template("ai_check.html", p=p, summary=summary,
                           report=report, usage=usage, err=err)
