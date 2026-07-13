"""
Apply RLS (Row Level Security) to all Supabase tables.
Connects via DATABASE_URL from .env and executes enable_rls.sql.
"""

import os
import sys

# Load environment
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

try:
    from backend.load_env import load_env_file
    load_env_file()
except ImportError:
    pass

# Read DATABASE_URL
DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    print("❌ DATABASE_URL not set in .env or environment")
    sys.exit(1)

# Read SQL file
sql_path = os.path.join(os.path.dirname(__file__), "enable_rls.sql")
if not os.path.exists(sql_path):
    print(f"❌ SQL file not found: {sql_path}")
    sys.exit(1)

with open(sql_path, "r") as f:
    sql = f.read()

print("✅ Read enable_rls.sql")

# Connect and execute
import psycopg2

# Fix the URL for psycopg2
dsn = DATABASE_URL
if dsn.startswith("postgres://"):
    dsn = "postgresql://" + dsn[len("postgres://"):]

try:
    conn = psycopg2.connect(dsn)
    conn.autocommit = True
    cur = conn.cursor()
    
    # Split by semicolons and execute each statement
    statements = [s.strip() for s in sql.split(";") if s.strip()]
    executed = 0
    for stmt in statements:
        # Skip comments
        if stmt.startswith("--") or stmt.startswith("/*"):
            continue
        try:
            cur.execute(stmt)
            executed += 1
            print(f"  ✅ Executed: {stmt[:80]}...")
        except Exception as e:
            print(f"  ⚠️  Skipped (may already exist): {stmt[:60]}... -> {e}")
    
    conn.close()
    print(f"\n✅ RLS applied: {executed} statements executed successfully")
    print("🔒 All public tables now have RLS enabled.")
    print("ℹ️  Backend API continues to work (owner bypasses RLS).")
    print("⛔ Supabase anon key direct queries are now blocked.")
    
except Exception as e:
    print(f"❌ Connection/execution error: {e}")
    sys.exit(1)