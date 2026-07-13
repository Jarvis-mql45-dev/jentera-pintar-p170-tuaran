"""
Apply recovery_schema.sql to Supabase PostgreSQL.
Reads DATABASE_URL from .env and executes the SQL file.
"""
import os
import sys

# Load .env manually
env_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(env_path):
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, val = line.split('=', 1)
                os.environ[key.strip()] = val.strip()

DATABASE_URL = os.environ.get('DATABASE_URL')
if not DATABASE_URL:
    print("❌ DATABASE_URL not found in .env")
    sys.exit(1)

print(f"🔌 Connecting to Supabase...")
print(f"   Host: {DATABASE_URL.split('@')[1].split(':')[0]}")

import psycopg2
conn = psycopg2.connect(DATABASE_URL)
conn.autocommit = True
cursor = conn.cursor()

# Read the SQL file
sql_path = os.path.join(os.path.dirname(__file__), 'backend', 'recovery_schema.sql')
with open(sql_path, 'r', encoding='utf-8') as f:
    sql_content = f.read()

# Split by semicolons to execute statements one by one
statements = [s.strip() for s in sql_content.split(';') if s.strip()]

success = 0
errors = 0
for stmt in statements:
    try:
        cursor.execute(stmt)
        success += 1
    except Exception as e:
        # IF NOT EXISTS handles most cases, but some errors are expected
        if 'already exists' in str(e) or 'duplicate' in str(e).lower():
            success += 1
            continue
        print(f"⚠️  {str(e)[:120]}")
        errors += 1

cursor.close()
conn.close()
print(f"\n✅ Schema applied: {success} statements executed ({errors} skipped)")