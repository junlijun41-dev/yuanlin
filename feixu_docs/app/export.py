# -*- coding: utf-8 -*-
"""导出引擎：把填报记录生成 Word。
两种模式：
1) 模板模式：用户上传的 docx 含 {{key}} 占位符 -> 替换
2) 自动模式：无模板时，按字段自动生成两列表格
"""
import os

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt

from .constants import PHASE_MAP, PROCESS_MAP


def _replace_placeholders(doc, mapping):
    """替换段落与表格单元格中的 {{key}}，尽量保留样式。"""
    def repl_in_paragraph(p):
        full = "".join(run.text for run in p.runs)
        if "{{" not in full:
            return
        for key, val in mapping.items():
            full = full.replace("{{%s}}" % key, str(val))
        # 残留未匹配占位符清空
        import re
        full = re.sub(r"\{\{[^}]+\}\}", "", full)
        for run in p.runs:
            run.text = ""
        if p.runs:
            p.runs[0].text = full
        else:
            p.add_run(full)

    for p in doc.paragraphs:
        repl_in_paragraph(p)
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for p in cell.paragraphs:
                    repl_in_paragraph(p)


def export_record(record, template, out_path, template_file=None):
    """生成 docx 到 out_path。"""
    data = record.data

    if template_file and os.path.exists(template_file):
        doc = Document(template_file)
        mapping = dict(data)
        mapping.update({
            "_title": record.title or template.title,
            "_project": record.project.name if record.project else "",
            "_code": template.code or "",
            "_date": record.created_at.strftime("%Y-%m-%d"),
        })
        _replace_placeholders(doc, mapping)
        doc.save(out_path)
        return out_path

    # 自动模式
    doc = Document()
    style = doc.styles["Normal"]
    style.font.name = "宋体"
    style.font.size = Pt(10.5)

    h = doc.add_paragraph()
    h.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = h.add_run(template.title)
    run.bold = True
    run.font.size = Pt(15)

    meta = doc.add_paragraph()
    meta.add_run("资料编号：%s    阶段：%s    工艺：%s" % (
        template.code or "—",
        PHASE_MAP.get(template.phase, ""),
        PROCESS_MAP.get(template.process, ""),
    )).font.size = Pt(9)

    fields = template.fields
    table = doc.add_table(rows=0, cols=2)
    table.style = "Table Grid"
    for f in fields:
        key = f.get("key")
        label = f.get("label", key)
        row = table.add_row().cells
        row[0].text = label
        row[0].width = Pt(140)
        row[1].text = str(data.get(key, ""))

    doc.add_paragraph()
    sign = doc.add_table(rows=1, cols=3)
    sign.style = "Table Grid"
    sc = sign.rows[0].cells
    sc[0].text = "施工单位（盖章）："
    sc[1].text = "监理单位："
    sc[2].text = "日期：%s" % record.created_at.strftime("%Y-%m-%d")

    doc.save(out_path)
    return out_path
