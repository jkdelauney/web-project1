import os

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

@app.route("/temp")
def temp():
    return "<!doctype html><html><head><title>Work In Progress</title></head><body><h1>Something will be here</h1></body></html>"

@app.route("/user/<username>")
def user(username):
    return render_template('users.html.j2', username=username)

@app.route("/api/<isbn>")
def api(isbn):
    return "this will be the api response"

@app.errorhandler(404)
def page_not_found(e):
    return render_template('http_error.html.j2', e=e), 404

if __name__ == '__main__':
    app.run(debug=True)
