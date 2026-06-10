import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from app.config import settings
from urllib.parse import urlparse

url = urlparse(settings.DATABASE_URL)
dbname = url.path[1:]
user = url.username
password = url.password
host = url.hostname
port = url.port

try:
    conn = psycopg2.connect(dbname="postgres", user=user, password=password, host=host, port=port)
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cur = conn.cursor()
    cur.execute(f"SELECT 1 FROM pg_catalog.pg_database WHERE datname = '{dbname}'")
    exists = cur.fetchone()
    if not exists:
        cur.execute(f'CREATE DATABASE "{dbname}"')
        print(f"Database '{dbname}' created successfully.")
    else:
        print(f"Database '{dbname}' already exists.")
    cur.close()
    conn.close()
except Exception as e:
    print(f"Error checking/creating database: {e}")
