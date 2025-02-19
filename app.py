from flask import Flask, render_template, redirect, session, flash, request
from regex import E
from flask_debugtoolbar import DebugToolbarExtension
from models import connect_db, db, User, Post
from forms import LoginForm, RegisterForm, PostForm
from sqlalchemy.exc import IntegrityError
import os
import re


app = Flask(__name__)


app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ECHO"] = True
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY")
app.config["DEBUG_TB_INTERCEPT_REDIRECTS"] = False


connect_db(app)

toolbar = DebugToolbarExtension(app)


@app.route("/")
def home_page():
    if "username" not in session:
        return redirect("/register")
    posts = Post.query.all()
    return render_template("show_posts.html", posts=posts)


@app.route("/register", methods=["POST", "GET"])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        email = form.email.data
        first_name = form.first_name.data
        last_name = form.last_name.data
        new_user = User.register(username, password, email, first_name, last_name)

        db.session.add(new_user)
        try:
            db.session.commit()
        except IntegrityError:
            form.username.errors.append("Username taken.  Please pick another")
            return render_template("register.html", form=form)
        session["username"] = new_user.username
        flash("Welcome! Successfully Created Your Account!", "success")
        return redirect(f"/users/{new_user.username}")

    return render_template("register.html", form=form)


@app.route("/login", methods=["GET", "POST"])
def login_user():
    form = LoginForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data

        user = User.authenticate(username, password)
        if user:
            flash(f"Welcome Back, {user.username}!", "primary")
            session["username"] = user.username
            return redirect(f"/users/{user.username}")
        else:
            form.username.errors = ["Invalid username/password."]

    return render_template("login.html", form=form)


@app.route("/users/<username>")
def show_user_info(username):
    if "username" not in session:
        flash("Please log in first!", "danger")
        return redirect("/")
    if not User.query.filter_by(username=username).first():
        flash("User does not exist", "danger")
        return redirect(f"/users/{session['username']}")

    user = User.query.filter_by(username=username).first()

    return render_template("user_info.html", user=user)


@app.route("/logout")
def logout():
    if "username" not in session:
        flash("You are already logged out!")
        return redirect("/")
    session.pop("username")
    flash("Goodbye!", "info")
    return redirect("/")


@app.route("/users/<username>/post/add", methods=["GET", "POST"])
def show_post_form(username):
    if "username" not in session:
        flash("Please log in first!", "danger")
        return redirect("/")
    user = User.query.filter_by(username=username).first()
    form = PostForm()

    if form.validate_on_submit():
        title = form.title.data
        content = form.content.data

        new_post = Post(title=title, content=content, username=username)
        db.session.add(new_post)
        db.session.commit()
        flash("Your post was created", "success")
        return redirect(f"/users/{username}")

    return render_template("new_post.html", user=user, form=form)


@app.route("/users/<username>/delete", methods=["POST"])
def delete_user(username):
    if session["username"] == "admin":
        user = User.query.filter_by(username=username).first()
        db.session.delete(user)
        db.session.commit()
        flash("User deleted by admin.", "success")
        return redirect("/admin/dashboard")
    else:
        session.pop("username")
        user = User.query.filter_by(username=username).first()
        db.session.delete(user)
        db.session.commit()
        flash("User deleted", "danger")
    return redirect("/")


@app.route("/post/<post_id>/update", methods=["GET", "POST"])
def edit_post_form(post_id):
    if "username" not in session:
        flash("Please log in first!", "danger")
        return redirect("/")

    if not Post.query.get(post_id):
        flash("Post does not exist", "danger")
        return redirect(f"/users/{session['username']}")

    post = Post.query.get(post_id)

    if post.username != session["username"] and session["username"] != "admin":
        flash("You do not have permission to edit this post.", "danger")
        return redirect(f"/users/{session['username']}")

    form = PostForm(obj=post)

    if form.validate_on_submit():
        post.title = form.title.data
        post.content = form.content.data
        db.session.commit()
        flash("Your post was edited", "success")
        return redirect(f"/users/{post.username}")

    return render_template("edit_post.html", post=post, form=form)


@app.route("/post/<post_id>/delete", methods=["POST"])
def delete_post(post_id):
    if "username" not in session:
        flash("Please log in first!", "danger")
        return redirect("/")

    if not Post.query.get(post_id):
        flash("Post does not exist", "danger")
        return redirect(f"/users/{session['username']}")

    post = Post.query.get(post_id)
    db.session.delete(post)
    db.session.commit()
    return redirect(request.referrer)

# admin routes
@app.route("/admin/dashboard")
def admin_dashboard():
    if session["username"] != 'admin':
        flash("You do not have permissions to this page.", "danger")
        return redirect("/")
    users = User.query.all()
    posts = Post.query.all()
    return render_template("admin_dashboard.html", users=users, posts=posts)