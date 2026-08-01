from flask import render_template


def register(app):
    app.register_error_handler(404, _not_found)
    app.register_error_handler(500, _server_error)


def _not_found(error):
    return render_template("errors/404.html"), 404


def _server_error(error):
    return render_template("errors/500.html"), 500
