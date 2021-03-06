import os
import json
import requests

from flask import Flask, session, render_template, request, redirect, url_for
from flask import jsonify, make_response
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

if not os.getenv("SECRET_KEY"):
    raise RuntimeError("SECRET_KEY is not set")

if not os.getenv("GOODREADS_KEY"):
    raise RuntimeError("GOODREADS_KEY is not set")
goodreads_key = os.getenv("GOODREADS_KEY")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))


@app.route("/")
def index():
    return render_template("index.html.j2", session=session)


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method != "POST":
        return render_template("signup.html.j2")
    username = request.form["username"]
    password = generate_password_hash(request.form["password"])
    displayname = request.form["displayname"]
    email = request.form["email"]

    user_lookup = db.execute(
        "select username from users where username=:username", {"username": username}
    ).fetchone()
    if user_lookup is not None:
        error_message = "Username is already taken"
        return render_template("signup.html.j2", error_message=error_message)

    db.execute(
        "insert into users (username, displayname, email, password) values (:username, :displayname, :email, :password)",
        {
            "username": username,
            "displayname": displayname,
            "email": email,
            "password": password,
        },
    )

    db.commit()

    session["username"] = user_lookup["username"]
    session["displayname"] = user_lookup["displayname"]
    session["user_id"] = user_lookup["id"]
    session["email"] = user_lookup["email"]

    return redirect(url_for("user", username=username))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        user_lookup = db.execute(
            "select trim(username) as username, trim(displayname) as displayname, password, email, id from users where username=:username",
            {"username": username},
        ).fetchone()

        if user_lookup is None:  # if book isn't found
            error_message = "User not found or password invalid"
            return render_template("login.html.j2", error_message=error_message)

        if check_password_hash(user_lookup["password"], password):
            session["username"] = user_lookup["username"]
            session["displayname"] = user_lookup["displayname"]
            session["user_id"] = user_lookup["id"]
            session["email"] = user_lookup["email"]
        else:
            error_message = "User not found or password invalid"
            return render_template("login.html.j2", error_message=error_message)

        return redirect(url_for("index"))

    error_message = None

    return render_template("login.html.j2", error_message=error_message)


@app.route("/logout")
def logout():
    # remove the username from the session if it is there
    session.pop("username", None)
    session.pop("displayname", None)
    session.pop("user_id", None)
    session.pop("email", None)
    return render_template("logout.html.j2")


@app.route("/user/<string:username>")
def user(username):
    userdata = {}
    user_lookup = db.execute(
        "select trim(username) as username, trim(displayname) as displayname,\
                            email from users where username=:username",
        {"username": username},
    ).fetchone()
    if user_lookup is None:
        userdata["message"] = "User not found"
    else:
        userdata["username"] = user_lookup["username"]
        userdata["displayname"] = user_lookup["displayname"]
        userdata["email"] = user_lookup["email"]
        if "username" in session and userdata["username"] == session["username"]:
            userdata["self"] = True
        else:
            userdata["self"] = False

    return render_template("users.html.j2", userdata=userdata)


@app.route("/search", methods=["GET", "POST"])
def search():
    if "username" not in session:
        return redirect(url_for("login"))

    query_result = None
    if request.method == "POST":
        query = "%" + request.form["query"] + "%"
        query_result = db.execute(
            "select * from books where isbn like :query or title like :query or author like :query",
            {"query": query},
        ).fetchall()
        if query_result == []:
            query_result = 0

    return render_template("search.html.j2", query_result=query_result)


# request details about a book by isbn returned as an HTML page
@app.route("/book/<string:isbn>")
def book(isbn):
    if "username" not in session:
        return redirect(url_for("login"))

    book_detail = db.execute(
        "select * from books where isbn=:isbn", {"isbn": isbn}
    ).fetchone()

    if book_detail is None:  # if book isn't found
        e = "The book you are looking for does not exist."
        return render_template("http_error.html.j2", e=e), 404
    # else request details from Good Reads
    good_reads = {}

    # request review counts from Good Reads api
    res = requests.get(
        "https://www.goodreads.com/book/review_counts.json",
        params={"key": goodreads_key, "isbns": isbn},
    )

    if res.status_code == 200:  # if on Good Reads assign variables
        res_dict = json.loads(res.text)

        good_reads["status"] = res.status_code
        good_reads["average_rating"] = res_dict["books"][0]["average_rating"]
        good_reads["ratings_count"] = res_dict["books"][0]["work_ratings_count"]
    else:  # if not just assign status code
        good_reads["status"] = res.status_code

    reviews = db.execute(
        "select trim(username) as username, trim(displayname) as displayname, review, rating, timestamp from reviews join users on reviews.user_id = users.id where book_id=:book_id",
        {"book_id": book_detail["id"]},
    ).fetchall()

    return render_template(
        "book.html.j2", book=book_detail, good_reads=good_reads, reviews=reviews
    )


# request details about a book by isbn returned in json format
@app.route("/api/<string:isbn>")
def api(isbn):
    # search for book in books by isbn passed through endpoint
    result = db.execute(
        "select * from books where isbn=:isbn", {"isbn": isbn}
    ).fetchone()
    api_response = {}

    if result is not None:  # check if book was found
        # search for review info, count number of reviews and average score
        rate_result = db.execute(
            "select count(*), round(avg(ALL rating), 1) from reviews where book_id=:book_id",
            {"book_id": result["id"]},
        ).fetchone()

        if rate_result["round"] is None:  # check if result has a value
            average_score = 0.0  # if not then set value to 0.0
        else:
            average_score = float(
                rate_result["round"]
            )  # cast value into type that json. can process

        api_response["title"] = result["title"]
        api_response["author"] = result["author"]
        api_response["year"] = int(
            result["year"]
        )  # cast year into int as it is char(4) in db
        api_response["isbn"] = result["isbn"]
        api_response["review_count"] = rate_result["count"]
        api_response["average_score"] = average_score

        http_response_code = (
            200  # set response code to 200, even though that is default
        )
    else:
        api_response["error"] = "isbn not found"  # human readable error message

        http_response_code = 404  # set response code to 404 as the isbn was not found

    return make_response(jsonify(api_response), http_response_code)


@app.errorhandler(404)
def page_not_found(e):
    return render_template("http_error.html.j2", e=e), 404


if __name__ == "__main__":
    app.run(debug=True)
