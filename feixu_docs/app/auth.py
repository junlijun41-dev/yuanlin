# -*- coding: utf-8 -*-
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required, login_user, logout_user

from .models import User, db

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        u = User.query.filter_by(username=request.form["username"].strip()).first()
        if u and u.check_password(request.form["password"]):
            login_user(u)
            return redirect(url_for("main.dashboard"))
        flash("用户名或密码错误", "error")
    return render_template("login.html")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"].strip()
        if User.query.filter_by(username=username).first():
            flash("用户名已存在", "error")
        else:
            u = User(username=username, name=request.form.get("name", ""),
                     role=request.form.get("role", "ziliaoyuan"))
            u.set_password(request.form["password"])
            db.session.add(u)
            db.session.commit()
            flash("注册成功，请登录", "ok")
            return redirect(url_for("auth.login"))
    return render_template("register.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))
