import os
import json

from flask import Flask, session, render_template
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

app = Flask(__name__)

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))


@app.route("/")
def index():
    return render_template('index.html.j2')

@app.route("/login")
def login():
    return render_template('login.html.j2')

@app.route("/logout")
def logout():
    return render_template('logout.html.j2')

@app.route("/user/<username>")
def user(username):
    return render_template('users.html.j2', username=username)

@app.route("/user")
def userx():
    return user('test')

@app.route("/search")
def search():
    return render_template('search.html.j2')

# request details about a book by isbn returned in json format
@app.route("/api/<string:isbn>")
def api(isbn):
    # search for book in books by isbn passed through endpoint
    result = db.execute("select * from books where isbn=:isbn", {'isbn': isbn}).fetchone()
    api_response = {}

    if result != None: # check if book was found
        # search for review info, count number of reviews and average score
        rate_result = db.execute("select count(*), round(avg(ALL rating), 1) from reviews where book_id=:book_id", {'book_id': result["id"]}).fetchone()

        if rate_result["round"] == None: # check if result has a value
            average_score = 0.0 # if not then set value to 0.0
        else:
            average_score = float(rate_result["round"]) # cast value into type that json. can process

        api_response["title"] = result["title"]
        api_response["author"] = result["author"]
        api_response["year"] = int(result["year"]) # cast year into int as it is char(4) in db
        api_response["isbn"] = result["isbn"]
        api_response["review_count"] = rate_result["count"]
        api_response["average_score"] = average_score

        http_response_code = 200 # set response code to 200, even though that is default
    else:
        api_response["error"] = "isbn not found" # human readable error message

        http_response_code = 404 # set response code to 404 as the isbn was not found

    json.dumps(api_response) # output response in json format
    return api_response, http_response_code

@app.errorhandler(404)
def page_not_found(e):
    return render_template('http_error.html.j2', e=e), 404

if __name__ == '__main__':
    app.run(debug=True)
