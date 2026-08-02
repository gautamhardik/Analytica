import os, sys
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))
import pymysql

db_host = os.getenv('DB_HOST', 'localhost')
db_port = int(os.getenv('DB_PORT', 3306))
db_user = os.getenv('DB_USER')
db_password = os.getenv('DB_PASSWORD')
db_name = os.getenv('DB_NAME')

base = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sql_dir = os.path.join(base, 'SQL')
files = [
    'create_dimensions.sql',
    'create_fact.sql',
    'indexes.sql',
    'views.sql',
    'reporting_sales_summary.sql',
    'reporting_category_summary.sql',
    'reporting_customer_summary.sql',
    'reporting_state_summary.sql'
]

conn = None
try:
    conn = pymysql.connect(host=db_host,user=db_user,password=db_password,port=db_port,autocommit=True,charset='utf8mb4')
    cur = conn.cursor()
    cur.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
    cur.execute(f"USE `{db_name}`;")
    for f in files:
        path = os.path.join(sql_dir, f)
        if not os.path.exists(path):
            print('Missing', path)
            continue
        print('Executing', f)
        with open(path, 'r', encoding='utf8') as fh:
            sql = fh.read()
        # split by ; to execute statements (simple heuristic)
        stmts = [s.strip() for s in sql.split(';') if s.strip()]
        for s in stmts:
            try:
                cur.execute(s)
            except Exception as e:
                print('Statement failed:', e)
    print('SQL import done')
except Exception as e:
    print('DB error', e)
    sys.exit(2)
finally:
    if conn:
        conn.close()
