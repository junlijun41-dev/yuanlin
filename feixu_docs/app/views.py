# -*- coding: utf-8 -*-
import json
import os

from flask import (Blueprint, abort, current_app, flash, redirect,
                   render_template, request, send_file, url_for)
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename

from .constants import (PHASES, PROCESSES, VOLUMES, WORKFLOW_ORDER)
from .export import export_record
from .models import FormRecord, FormTemplate, Project, Requirement, TreeLedger, db
from .template_parse import extract_fields

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


def _save_template_file(tpl, file):
    """保存上传的 docx/xlsx，自动解析占位符生成字段。返回提取的字段数。"""
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in (".docx", ".xlsx"):
        raise ValueError("仅支持 .docx 或 .xlsx 文件")
    fn = "tpl_%d_%s%s" % (tpl.id, "f", ext)  # 固定名，覆盖式
    path = os.path.join(current_app.config["TEMPLATE_DIR"], fn)
    file.save(path)
    tpl.docx_file = fn
    fields = extract_fields(path)
    if fields:
        tpl.fields = fields
    return len(fields)


@main_bp.route("/templates/<int:tid>/upload", methods=["POST"])
@login_required
def template_upload(tid):
    """为已有模板上传 docx/xlsx 文件，自动重建字段。"""
    tpl = FormTemplate.query.get_or_404(tid)
    file = request.files.get("docx")
    if not file or not file.filename:
        flash("请选择文件", "error")
        return redirect(url_for("main.templates_list"))
    try:
        n = _save_template_file(tpl, file)
        db.session.commit()
        flash("模板已上传，自动识别 %d 个字段；可点「编辑字段」调整标签/必填" % n, "ok")
    except ValueError as e:
        flash(str(e), "error")
    return redirect(url_for("main.template_edit", tid=tpl.id))


@main_bp.route("/templates/upload_new", methods=["POST"])
@login_required
def template_upload_new():
    """上传文件直接新建模板（占位符自动建表）。"""
    file = request.files.get("file")
    if not file or not file.filename:
        flash("请选择模板文件", "error")
        return redirect(url_for("main.templates_list"))
    tpl = FormTemplate(code=request.form.get("code", ""),
                       title=request.form.get("title", "").strip() or os.path.splitext(file.filename)[0],
                       phase=request.form.get("phase"), process=request.form.get("process"),
                       volume=request.form.get("volume"))
    db.session.add(tpl)
    db.session.flush()  # 拿到 tpl.id
    try:
        n = _save_template_file(tpl, file)
        db.session.commit()
        flash("模板已创建，自动识别 %d 个字段，请检查后保存" % n, "ok")
        return redirect(url_for("main.template_edit", tid=tpl.id))
    except ValueError as e:
        db.session.rollback()
        flash(str(e), "error")
        return redirect(url_for("main.templates_list"))


@main_bp.route("/templates/<int:tid>/edit", methods=["GET", "POST"])
@login_required
def template_edit(tid):
    """编辑模板字段：调整标签/类型/必填/下拉选项。"""
    tpl = FormTemplate.query.get_or_404(tid)
    if request.method == "POST":
        keys = request.form.getlist("key")
        labels = request.form.getlist("label")
        types = request.form.getlist("type")
        opts = request.form.getlist("options")
        reqs = set(request.form.getlist("required"))  # 勾选的 key
        fields = []
        for i, k in enumerate(keys):
            k = k.strip()
            if not k:
                continue
            f = {"key": k, "label": (labels[i].strip() or k),
                 "type": types[i] if i < len(types) else "text",
                 "required": k in reqs}
            if f["type"] == "select" and i < len(opts) and opts[i].strip():
                f["options"] = [o.strip() for o in opts[i].split(",") if o.strip()]
            fields.append(f)
        tpl.fields = fields
        tpl.title = request.form.get("title", tpl.title).strip() or tpl.title
        tpl.code = request.form.get("code", tpl.code)
        tpl.phase = request.form.get("phase", tpl.phase)
        tpl.process = request.form.get("process", tpl.process)
        tpl.volume = request.form.get("volume", tpl.volume)
        db.session.commit()
        flash("字段已保存", "ok")
        return redirect(url_for("main.templates_list"))
    return render_template("template_edit.html", tpl=tpl, phases=PHASES,
                           processes=PROCESSES, volumes=VOLUMES)


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
    tpl_file = None
    if tpl.docx_file:
        tpl_file = os.path.join(current_app.config["TEMPLATE_DIR"], tpl.docx_file)
    out_path, ext = export_record(rec, tpl, current_app.config["EXPORT_DIR"], template_file=tpl_file)
    dl_name = "C-%04d_%s%s" % (rec.id, (tpl.code or tpl.title or "record"), ext)
    return send_file(out_path, as_attachment=True, download_name=dl_name)


@main_bp.route("/records/<int:rid>/delete", methods=["POST"])
@login_required
def record_delete(rid):
    rec = FormRecord.query.get_or_404(rid)
    pid = rec.project_id
    db.session.delete(rec)
    db.session.commit()
    flash("已删除", "ok")
    return redirect(url_for("main.project_detail", pid=pid))


# ---------------- 需求清单 ----------------
@main_bp.route("/requirements")
@login_required
def requirements():
    """需求清单：手动登记待做/在做/已完成的事项，页面默认空白，便于回看与继续完善。"""
    items = Requirement.query.order_by(Requirement.created_at.desc()).all()
    return render_template("requirements.html", items=items,
                           status_labels=Requirement.STATUS_LABELS)


@main_bp.route("/requirements/add", methods=["POST"])
@login_required
def requirement_add():
    title = request.form.get("title", "").strip()
    if not title:
        flash("请填写需求标题", "error")
        return redirect(url_for("main.requirements"))
    r = Requirement(title=title, detail=request.form.get("detail", "").strip(),
                    status=request.form.get("status", "todo"), created_by=current_user.id)
    db.session.add(r)
    db.session.commit()
    flash("需求已添加", "ok")
    return redirect(url_for("main.requirements"))


@main_bp.route("/requirements/<int:rid>/status", methods=["POST"])
@login_required
def requirement_status(rid):
    r = Requirement.query.get_or_404(rid)
    target = request.form.get("status")
    if target in Requirement.STATUS_LABELS:
        r.status = target
        db.session.commit()
        flash("状态已更新", "ok")
    return redirect(url_for("main.requirements"))


@main_bp.route("/requirements/<int:rid>/delete", methods=["POST"])
@login_required
def requirement_delete(rid):
    r = Requirement.query.get_or_404(rid)
    db.session.delete(r)
    db.session.commit()
    flash("需求已删除", "ok")
    return redirect(url_for("main.requirements"))
