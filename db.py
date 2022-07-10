""" database access
docs:
* http://initd.org/psycopg/docs/
* http://initd.org/psycopg/docs/pool.html
* http://initd.org/psycopg/docs/extras.html#dictionary-like-cursor
"""

from contextlib import contextmanager
import logging
import os

from flask import current_app, g

import psycopg2
from psycopg2.pool import ThreadedConnectionPool
from psycopg2.extras import DictCursor

import json

pool = None

def setup():
    global pool
    DATABASE_URL = 'postgres://safuxyhlbogepr:09e07907cb39aeae2601d19c050a01e4113756b4ace8432df42f4b378e008758@ec2-3-225-204-194.compute-1.amazonaws.com:5432/dc0jgvepfrlfcv'
    current_app.logger.info(f"creating db connection pool")
    pool = ThreadedConnectionPool(1, 4, dsn=DATABASE_URL, sslmode='require')

@contextmanager
def get_db_connection():
    try:
        connection = pool.getconn()
        yield connection
    finally:
        pool.putconn(connection)

@contextmanager
def get_db_cursor(commit=False):
    with get_db_connection() as connection:
      cursor = connection.cursor(cursor_factory=DictCursor)
      try:
          yield cursor
          if commit:
              connection.commit()
      finally:
          cursor.close()

def upload_font(data, filename, desc, downloads,user_data):
    with get_db_cursor(True) as cur:
        current_app.logger.info("inserting font file into fonts table")
        cur.execute("insert into fonts (fname, data, description, downloads, auth_id) values (%s, %s, %s, %s, %s)", (filename, data, desc, downloads,user_data))

def get_font_ids():
    with get_db_cursor() as cur:
        cur.execute("select font_id from fonts order by font_id desc limit 12 ;")
        return [r['font_id'] for r in cur]

def get_font_names():
    with get_db_cursor() as cur:
        cur.execute("select fname from fonts order by font_id desc limit 12 ;")
        return [r['fname'] for r in cur]

def get_font(font_id):
    with get_db_cursor() as cur:
        cur.execute('SELECT * FROM fonts where font_id=%s',(font_id,))
        return cur.fetchone()

def edit_font_desc(font_id, new_desc):
    with get_db_cursor(True) as cur:
        cur.execute("UPDATE fonts SET description=%s WHERE font_id=%s", (new_desc, font_id))

def download_font(font_id):
    with get_db_cursor(True) as cur:
        cur.execute('UPDATE fonts SET downloads=downloads+1 WHERE font_id=%s', (font_id,))
        cur.execute('SELECT data FROM fonts where font_id=%s',(font_id,))
        return cur.fetchone()

def delete_font(font_id):
    with get_db_cursor(True) as cur:
        cur.execute('DELETE FROM fonts where font_id=%s',(font_id,))

def get_font_user_data(font_id):
    with get_db_cursor(True) as cur:
        cur.execute('SELECT auth_id from fonts WHERE font_id=%s', (font_id,))
        return cur.fetchone()

def add_user(user_data):
    returning_user = False
    json_user_data = json.loads(user_data)
    with get_db_cursor(True) as cur:
        cur.execute('SELECT auth_id from users')
        for r in cur:
            res = r[0]
            current_user_data = json.loads(res)
            if current_user_data['email'] == json_user_data['email']:
                returning_user = True
                break
        if not returning_user:
            cur.execute('INSERT INTO users (auth_id, bio) VALUES (%s)', (user_data, "We don't know much about this user... yet!"))

def get_user_data(user_id):
    with get_db_cursor(True) as cur:
        cur.execute('SELECT auth_id from users WHERE user_id=%s', (user_id,))
        return cur.fetchone()

def get_user_font_info(user_id):
    with get_db_cursor() as cur:
        cur.execute('SELECT auth_id from users where user_id=%s', (user_id,))
        auth_id = cur.fetchone()[0]
        json_user_data = json.loads(auth_id)
        cur.execute('SELECT * from fonts')
        font_info = []
        for r in cur:
            current_user_data = json.loads(r['auth_id'])
            if current_user_data['email'] == json_user_data['email']:
                font_info.append([r['font_id'], r['fname']])
        return font_info

def get_user_id(user_data):
    json_user_data = json.loads(user_data)
    with get_db_cursor(True) as cur:
        cur.execute('SELECT * from users')
        for r in cur:
            current_user_data = json.loads(r['auth_id'])
            if current_user_data['email'] == json_user_data['email']:
                return r['user_id']
        return -1

def get_uploader_id(font_id):
    with get_db_cursor(True) as cur:
        cur.execute('SELECT auth_id from fonts where font_id=%s', (font_id,))
        auth_id = cur.fetchone()[0]
        json_user_data = json.loads(auth_id)
        cur.execute('SELECT * from users')
        for r in cur:
            current_user_data = json.loads(r['auth_id'])
            if current_user_data['email'] == json_user_data['email']:
                return r['user_id']
        return -1

def get_user_bio(user_id):
    with get_db_cursor(True) as cur:
        cur.execute('SELECT bio from users where user_id=%s', (user_id,))
        return cur.fetchone()[0]

def edit_user_bio(user_id, new_bio):
    with get_db_cursor(True) as cur:
        cur.execute('UPDATE users set bio=%s where user_id=%s', (new_bio, user_id))