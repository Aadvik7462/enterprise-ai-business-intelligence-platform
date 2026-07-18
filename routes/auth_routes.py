from flask import Blueprint, render_template, request, redirect, url_for, session, flash

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/")
def home():
    if "user" in session:
        return redirect(url_for("dashboard.dashboard"))
    return redirect(url_for("auth.login"))


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        if email == "admin@gmail.com" and password == "admin123":
            session["user"] = email
            flash("Login successful!", "success")
            return redirect(url_for("dashboard.dashboard"))

        flash("Invalid email or password", "error")

    return render_template("login.html")


@auth_bp.route("/logout")
def logout():
    session.pop("user", None)
    session.pop("uploaded_file", None)
    session.pop("cleaning_report", None)
    session.pop("cleaned_file", None)

    flash("Logged out successfully", "success")
    return redirect(url_for("auth.login"))