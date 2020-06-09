import csv
import os
import sys

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))


def main():
    # db.execute("DROP TABLE IF EXISTS books CASCADE")
    db.execute(
        "CREATE TABLE IF NOT EXISTS books (id SERIAL PRIMARY KEY,isbn varchar(13) NOT NULL, title character varying NOT NULL, author character varying NOT NULL, year character(4) NOT NULL)"
    )

    r_count = 0
    f = open("books.csv")
    reader = csv.reader(f)
    next(reader)  # advance past column headers
    for isbn, title, author, year in reader:  # isbn, title, author, year
        db.execute(
            "INSERT INTO books (isbn, title, author, year) VALUES (:isbn, :title, :author, :year)",
            {"isbn": isbn, "title": title, "author": author, "year": year},
        )
        sys.stdout.write(".")
        sys.stdout.flush()
        r_count += 1
    db.commit()
    print(f"\nRecords imported: {r_count}")


if __name__ == "__main__":
    main()
