from flask import render_template

from app.admin import admin_bp


@admin_bp.route("/login")
def login():
    return render_template("admin/login.html")
