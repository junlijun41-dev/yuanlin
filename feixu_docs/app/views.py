# -*- coding: utf-8 -*-
import json
import os

from flask import (Blueprint, abort, current_app, flash, redirect,
                   render_template, request, send_file, url_for)
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename

from .constants import (PHASES, PROCESSES, VOLUMES, WORKFLOW_ORDER)
from .export import export_record
from .models import FormRecord, FormTemplate, Project, TreeLedger, db

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
@login_required
def dashboard():
    projects = Project.query.order_by(Project.created_at.desc()).all()
    stats = {
        "projects": Project.query.count(),
        "templates": FormTemplate.query.count(),
        "records": FormRecord.query.count(),
    }
    return render_template("dashboard.html", projects=projects, stats=stats)


# ---------------- 项目 ----------------
@main_bp.route("/projects/new", methods=["POST"])
@login_required
def project_new():
    p = Project(name=request.form["name"].strip(), code=request.form.get("code", ""),
                contractor=request.form.get("contractor", ""),
                supervisor=request.form.get("supervisor", ""),
                owner=request.form.get("owner", ""))
    db.session.add(p)
    db.session.commit()
    flash("项目已创建", "ok")
    return redirect(url_for("main.project_detail", pid=p.id))


@main_bp.route("/projects/<int:pid>")
@login_required
def project_detail(pid):
    p = Project.query.get_or_404(pid)
    records = FormRecord.query.filter_by(project_id=pid).order_by(FormRecord.updated_at.desc()).all()
    templates = FormTemplate.query.order_by(FormTemplate.volume, FormTemplate.code).all()
    # 按册分组记录
    by_volume = {}
    for r in records:
        by_volume.setdefault(r.template.volume, []).append(r)
    return render_template("project.html", p=p, records=records, templates=templates,
                           by_volume=by_volume, phases=PHASES, processes=PROCESSES, volumes=VOLUMES)


# ---------------- 模板管理 ----------------
@main_bp.route("/templates")
@login_required
def templates_list():
    tpls = FormTemplate.query.order_by(FormTemplate.volume, FormTemplate.code).all()
    return render_template("templates.html", templates=tpls, phases=PHASES,
                           processes=PROCESSES, volumes=VOLUMES)


@main_bp.route("/templates/new", methods=["POST"])
@login_required
def template_new():
    tpl = FormTemplate(code=request.form.get("code", ""), title=request.form["title"].strip(),
                       phase=request.form.get("phase"), process=request.form.get("process"),
                       volume=request.form.get("volume"))
    # 字段：每行 "key|标签|类型|必填"
    fields = []
    for line in request.form.get("fields_raw", "").splitlines():
        line = line.strip()
        if not line:
            continue
        parts = [x.strip() for x in line.split("|")]
        f = {"key": parts[0], "label": parts[1] if len(parts) > 1 else parts[0],
             "type": parts[2] if len(parts) > 2 else "text",
             "required": (len(parts) > 3 and parts[3] in ("1", "必填", "y", "Y"))}
        fields.append(f)
    tpl.fields = fields
    db.session.add(tpl)
    db.session.commit()
    flash("模板已创建", "ok")
    return redirect(url_for("main.templates_list"))


@main_bp.route("/templates/<int:tid>/upload", methods=["POST"])
@login_required
def template_upload(tid):
    """上传 docx 模板文件（含 {{key}} 占位符）"""
    tpl = FormTemplate.query.get_or_404(tid)
    file = request.files.get("docx")
    if file and file.filename.lower().endswith(".docx"):
        fn = "tpl_%d_%s" % (tpl.id, secure_filename(file.filename))
        path = os.path.join(current_app.config["TEMPLATE_DIR"], fn)
        file.save(path)
        tpl.docx_file = fn
        db.session.commit()
        flash("模板文件已上传，导出将套用该格式", "ok")
    else:
        flash("请上传 .docx 文件", "error")
    return redirect(url_for("main.templates_list"))


# ---------------- 填报记录 ----------------
@main_bp.route("/projects/<int:pid>/records/new/<int:tid>", methods=["GET", "POST"])
@login_required
def record_new(pid, tid):
    p = Project.query.get_or_404(pid)
    tpl = FormTemplate.query.get_or_404(tid)
    if request.method == "POST":
        data, missing = _collect_fields(tpl)
        if missing:
            flash("以下必填项未填：" + "、".join(missing), "error")
            return render_template("record_form.html", p=p, tpl=tpl, rec=None,
                                   data=data)
        rec = FormRecord(project_id=pid, template_id=tid,
                         title=request.form.get("_title") or tpl.title,
                         created_by=current_user.id)
        rec.data = data
        db.session.add(rec)
        db.session.commit()
        flash("填报已保存", "ok")
        return redirect(url_for("main.project_detail", pid=pid))
    return render_template("record_form.html", p=p, tpl=tpl, rec=None, data={})


@main_bp.route("/records/<int:rid>/edit", methods=["GET", "POST"])
@login_required
def record_edit(rid):
    rec = FormRecord.query.get_or_404(rid)
    tpl = rec.template
    if request.method == "POST":
        data, missing = _collect_fields(tpl)
        if missing:
            flash("以下必填项未填：" + "、".join(missing), "error")
            return render_template("record_form.html", p=rec.project, tpl=tpl, rec=rec, data=data)
        rec.data = data
        rec.title = request.form.get("_title") or tpl.title
        db.session.commit()
        flash("已更新", "ok")
        return redirect(url_for("main.project_detail", pid=rec.project_id))
    return render_template("record_form.html", p=rec.project, tpl=tpl, rec=rec, data=rec.data)


def _collect_fields(tpl):
    data, missing = {}, []
    for f in tpl.fields:
        val = request.form.get(f["key"], "").strip()
        data[f["key"]] = val
        if f.get("required") and not val:
            missing.append(f["label"])
    return data, missing


@main_bp.route("/records/<int:rid>/step", methods=["POST"])
@login_required
def record_step(rid):
    """推进报验状态机：交底→施工→自检→报验→验收，禁止跳步"""
    rec = FormRecord.query.get_or_404(rid)
    target = request.form.get("target")
    cur_idx = WORKFLOW_ORDER.index(rec.workflow_step) if rec.workflow_step in WORKFLOW_ORDER else 0
    if target in WORKFLOW_ORDER:
        t_idx = WORKFLOW_ORDER.index(target)
        if t_idx == cur_idx + 1:
            rec.workflow_step = target
            db.session.commit()
            flash("状态已推进至：" + target, "ok")
        elif t_idx <= cur_idx:
            flash("不能回退或重复当前步骤", "error")
        else:
            flash("报验顺序错误：必须按 交底→施工→自检→报验→验收 逐步推进", "error")
    return redirect(url_for("main.project_detail", pid=rec.project_id))


@main_bp.route("/records/<int:rid>/export")
@login_required
def record_export(rid):
    rec = FormRecord.query.get_or_404(rid)
    tpl = rec.template
    out_name = "C-%04d_%s.docx" % (rec.id, (tpl.code or tpl.title))
    out_path = os.path.join(current_app.config["EXPORT_DIR"], secure_filename(out_name))
    tpl_file = None
    if tpl.docx_file:
        tpl_file = os.path.join(current_app.config["TEMPLATE_DIR"], tpl.docx_file)
    export_record(rec, tpl, out_path, template_file=tpl_file)
    return send_file(out_path, as_attachment=True, download_name=out_name)


@main_bp.route("/records/<int:rid>/delete", methods=["POST"])
@login_required
def record_delete(rid):
    rec = FormRecord.query.get_or_404(rid)
    pid = rec.project_id
    db.session.delete(rec)
    db.session.commit()
    flash("已删除", "ok")
    return redirect(url_for("main.project_detail", pid=pid))
