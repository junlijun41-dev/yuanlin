# -*- coding: utf-8 -*-
import json
from datetime import datetime

from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash

db = SQLAlchemy()


class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    name = db.Column(db.String(64))
    role = db.Column(db.String(32), default="ziliaoyuan")  # ziliaoyuan/jingli/jianli/admin
    password_hash = db.Column(db.String(256))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, pw):
        self.password_hash = generate_password_hash(pw)

    def check_password(self, pw):
        return check_password_hash(self.password_hash, pw)

    @property
    def role_label(self):
        return {
            "ziliaoyuan": "资料员",
            "jingli": "项目经理",
            "jianli": "监理",
            "admin": "管理员",
        }.get(self.role, self.role)


class Requirement(db.Model):
    """需求清单：手动登记待做/在做/已完成的事项，便于回看与继续完善。

    项目尚不确定哪些环节能自动化，先用这张表手动记录需求，页面默认空白、随时增删。
    """
    __tablename__ = "requirements"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)     # 需求标题
    detail = db.Column(db.Text)                            # 详细说明（可留空）
    status = db.Column(db.String(16), default="todo")      # todo/doing/done
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    author = db.relationship("User")

    STATUS_LABELS = {"todo": "待办", "doing": "进行中", "done": "已完成"}

    @property
    def status_label(self):
        return self.STATUS_LABELS.get(self.status, self.status)


class Project(db.Model):
    __tablename__ = "projects"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    code = db.Column(db.String(64))           # 工程编号
    contractor = db.Column(db.String(200))    # 施工单位
    supervisor = db.Column(db.String(200))    # 监理单位
    owner = db.Column(db.String(200))         # 建设单位/甲方
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    records = db.relationship("FormRecord", backref="project", cascade="all, delete-orphan")
    trees = db.relationship("TreeLedger", backref="project", cascade="all, delete-orphan")


class TreeLedger(db.Model):
    """现状树木核查台账：待注射/待修剪/待嫁接/待更新明细"""
    __tablename__ = "trees"
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"))
    tree_no = db.Column(db.String(64))        # 树木编号
    species = db.Column(db.String(64))        # 树种
    dbh = db.Column(db.String(32))            # 胸径
    location = db.Column(db.String(200))      # 点位
    process = db.Column(db.String(32))        # 适用工艺
    note = db.Column(db.String(255))


class FormTemplate(db.Model):
    """表单模板：字段 schema(JSON) + 可选的 docx/xlsx 导出模板文件"""
    __tablename__ = "templates"
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(32))           # 资料编号 如 C1-001
    title = db.Column(db.String(200), nullable=False)
    phase = db.Column(db.String(32))          # 阶段
    process = db.Column(db.String(32))        # 工艺
    volume = db.Column(db.String(8))          # 组卷册 C1..C8
    fields_json = db.Column(db.Text)          # 字段定义 JSON
    docx_file = db.Column(db.String(255))     # 上传的 docx 模板文件名(可选)
    is_seed = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    records = db.relationship("FormRecord", backref="template", cascade="all, delete-orphan")

    @property
    def fields(self):
        try:
            return json.loads(self.fields_json or "[]")
        except (ValueError, TypeError):
            return []

    @fields.setter
    def fields(self, value):
        self.fields_json = json.dumps(value, ensure_ascii=False)


class FormRecord(db.Model):
    """填报记录：一条 = 一张填好的表"""
    __tablename__ = "records"
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"))
    template_id = db.Column(db.Integer, db.ForeignKey("templates.id"))
    title = db.Column(db.String(200))         # 记录标题(如 "3号树打孔注射记录")
    data_json = db.Column(db.Text)            # 填报数据 JSON
    workflow_step = db.Column(db.String(32), default="jiaodi")  # 报验状态
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    author = db.relationship("User")

    @property
    def data(self):
        try:
            return json.loads(self.data_json or "{}")
        except (ValueError, TypeError):
            return {}

    @data.setter
    def data(self, value):
        self.data_json = json.dumps(value, ensure_ascii=False)
