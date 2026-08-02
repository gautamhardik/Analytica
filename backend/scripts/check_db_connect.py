import os, sys
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))
user = os.getenv('DB_USER')
password = os.getenv('DB_PASSWORD')
host = os.getenv('DB_HOST')
port = int(os.getenv('DB_PORT') or 3306)
db = os.getenv('DB_NAME')
print(f'Using DB: {user}@{host}:{port}/{db}')
try:
    import pymysql
    conn = pymysql.connect(host=host, user=user, password=password, port=port, connect_timeout=5)
    cur = conn.cursor()
    cur.execute('SELECT VERSION()')
    print('MySQL version:', cur.fetchone()[0])
    cur.execute('SHOW DATABASES LIKE %s', (db,))
    if cur.fetchone():
        print('Database exists')
    else:
        print('Database does NOT exist')
    cur.close()
    conn.close()
except Exception as e:
    print('DB connect error:', repr(e))
    sys.exit(2)
