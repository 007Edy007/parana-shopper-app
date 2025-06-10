import sqlite3

def connect_db():
    conn = sqlite3.connect('parana.db')
    conn.execute("PRAGMA foreign_keys = ON;")  # Ensure foreign keys are enforced
    return conn, conn.cursor()

def close_db(conn):
    conn.close()
