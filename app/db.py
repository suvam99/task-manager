import psycopg2
from psycopg2 import OperationalError


def get_connection():
    try:
        conn = psycopg2.connect(
            dbname="taskdb",
            user="taskuser",
            password="0908",
            host="localhost",
            port="5432",
        )
        return conn
    except OperationalError as e:
        print("Database connection failed:", e)
        return None
