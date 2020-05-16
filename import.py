import csv, os, sys

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

def main():
    r_count = 0
    f = open("books.csv")
    reader = csv.reader(f)
    next(reader)
    for isbn, title, author, year in reader: # isbn, title, author, year
        db.execute("INSERT INTO books (isbn, title, author, year) VALUES (:isbn, :title, :author, :year)",
                   {"isbn": isbn, "title": title, "author": author, "year": year})
        sys.stdout.write(".")
        sys.stdout.flush()
        r_count += 1
    db.commit()
    print(f"\nRecords imported: {r_count}")

if __name__ == "__main__":
    main()
