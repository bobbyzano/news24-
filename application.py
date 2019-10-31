from flask import Flask, render_template, request, redirect, flash, url_for, session, logging, flash
from data import Articles
from flask_mysqldb import MySQL
from passlib.hash import sha256_crypt
from wtforms import Form, StringField, TextAreaField, PasswordField, validators
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps  # this is used to block unauthorized access of the dashboard when not in use

app = Flask(__name__)
app.secret_key = "secret1234"
# configure database

app.config["MYSQL_HOST"] = "localhost"
app.config["MYSQL_USER"] = "Bobby"
app.config["MYSQL_PASSWORD"] = "1234"
app.config["MYSQL_DB"] = "blackbook"
app.config["MYSQL_CURSORCLASS"] = "DictCursor"

mysql = MySQL(app)

# Articles = Articles()


@app.route("/")
def homePage():
    return render_template("index.html")


@app.route("/about")
def about():
    return render_template("about.html")


def is_logged_in(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash("Unauthorized access, Please login", "danger")
            return redirect(url_for("login"))

    return wrapped


@app.route("/logout")
@is_logged_in
def logout():
    session.clear()
    flash("You are now logged out", "success")
    return redirect(url_for("login"))


@app.route("/articles")
@is_logged_in
def articles():
    cur = mysql.connection.cursor()

    result = cur.execute("SELECT * FROM articles")
    articles = cur.fetchall()

    if result > 0:
        return render_template("articles.html", articles=articles)
    else:
        msg = "No articles found"
        return render_template("articles.html", msg=msg)

    cur.close()
    return render_template("articles.html", articles=Articles)








@app.route("/article/<string:id>/")
def article(id):
    cur = mysql.connection.cursor()

    result = cur.execute("SELECT * FROM articles WHERE id = %s", [id])
    article = cur.fetchone()

    if result > 0:
        return render_template("article.html", article=article)
    else:
        msg = "No articles found"
        return render_template("articles.html", msg=msg)

    cur.close()

    return render_template("article.html", id=id)


class MyForm(Form):
    name = StringField(u'Name', validators=
    [validators.input_required(), validators.Length(min=3, max=50)])

    email = StringField(u'Email', validators=
    [validators.input_required(), validators.Length(min=3, max=50)])

    username = StringField(u'Username', validators=
    [validators.input_required(), validators.length(min=3, max=50)])

    password = PasswordField('Password', [
        validators.DataRequired(),
        validators.EqualTo('confirm', message='Passwords must match')
    ])
    confirm = PasswordField('Confirm Password')


@app.route("/register", methods=["GET", "POST"])
def register():
    form = MyForm(request.form)
    if request.method == "POST" and form.validate():
        name = form.name.data
        email = form.email.data
        username = form.username.data
        password = sha256_crypt.encrypt(str(form.password.data))

        # Create cursor
        cur = mysql.connection.cursor()

        cur.execute("INSERT INTO newsreg (name, email, username,password) VALUES(%s, %s, %s, %s)",
                    (name, email, username, password))

        # commit to database
        mysql.connection.commit()

        # close connecction
        cur.close()

        # flash message
        flash("you have successfully registered", "success")
        return redirect("/login")

    # if request.method == "GET":
    return render_template("register.html", form=form)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        # get form fields

        username = request.form["username"]
        password_candidate = request.form["password"]

        # create cursor
        cur = mysql.connection.cursor()

        # get user by name
        result = cur.execute("SELECT * FROM newsreg WHERE username = %s", [username])

        if result > 0:
            #     get the hash
            data = cur.fetchone()
            password = data["password"]

            #  compare password
            if sha256_crypt.verify(password_candidate, password):
                app.logger.info("Password matched")
                session["logged_in"] = True
                session["username"] = username

                flash("you are succesfully logged in", "success")
                return redirect(url_for("dashboard"))

            else:
                error = "Invalid login credentials"

                return render_template("login.html", error=error)

        else:
            error = "User not found"
            return render_template("login.html", error=error)

    return render_template("login.html", name="login")



#

@app.route("/dashboard")
@is_logged_in
def dashboard():
    cur = mysql.connection.cursor()

    result = cur.execute("SELECT * FROM articles")
    articles = cur.fetchall()

    if result > 0:
        return render_template("dashboard.html", articles=articles)
    else:
        msg = "No articles found"
        return render_template("dashboard.html", msg=msg)

    cur.close()


class ArticleForm(Form):


    title = StringField('Title', validators=
    [validators.input_required(), validators.length(min=3, max=200)])

    body = TextAreaField('Body', validators=
    [validators.input_required(), validators.length(min=30)])


# add article

@app.route("/add_article", methods=["GET", "POST"] )
@is_logged_in
def add_article():
    form = ArticleForm(request.form)
    if request.method == "POST" and form.validate():
        title = form.title.data
        body = form.body.data

        cur = mysql.connection.cursor()

        cur.execute("INSERT INTO articles (title, body, author) VALUES( %s, %s, %s)", (title,body, session['username']))

        mysql.connection.commit()

        cur.close()

        flash("Article created", "success")

        return redirect(url_for("dashboard"))

    return render_template("add_article.html", form=form)



# edit Articles


@app.route("/edit_article/<string:id>", methods=["GET", "POST"] )
@is_logged_in
def edit_article(id):
    # Create cursor

    cur = mysql.connection.cursor()

    # Get article by id

    result= cur.execute("SELECT * FROM articles WHERE id = %s", [id])
    article = cur.fetchone()

    # Get form

    form = ArticleForm(request.form)

    # populate article form field

    form.title.data = article["title"]
    form.body.data = article["body"]

    if request.method == "POST" and form.validate():
        title = request.form["title"]
        body = request.form["body"]

        cur = mysql.connection.cursor()

        cur.execute("UPDATE articles SET title =%s, body=%s WHERE id = %s", (title, body, id))

        mysql.connection.commit()

        cur.close()

        flash("Article updated", "success")

        return redirect(url_for("dashboard"))

    return render_template("edit_article.html", form=form)


# Delete article

@app.route("/delete_article/<string:id>", methods=["POST"])
@is_logged_in
def delete_article(id):
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM articles WHERE id =%s", [id])
    mysql.connection.commit()
    cur.close()
    flash("Article Deleted", "success")

    return redirect(url_for("dashboard"))





if __name__ == " __main__":
    app.run(debug=True)
