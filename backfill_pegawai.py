"""
Backfill script untuk mengisi no_kp dan no_telefon yang kosong
dalam table pegawai_penyelaras dengan memadankan nama_penuh
terhadap pengundi dalam table pengundi.

Strategy padanan (tiered):
1. Exact match (UPPER)
2. Fuzzy match (token Jaccard similarity >= 0.7)
"""
import os
import sys
import re
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from backend.config import settings

USE_POSTGRES = bool(settings.DATABASE_URL and settings.DATABASE_URL.strip())


def normalize_name(name):
    if not name:
        return ""
    name = name.upper()
    name = re.sub(r'[^\w\s]', ' ', name)
    name = re.sub(r'\s+', ' ', name).strip()
    return name


def get_tokens(name):
    return set(normalize_name(name).split())


def token_similarity(name1, name2):
    tokens1 = get_tokens(name1)
    tokens2 = get_tokens(name2)
    if not tokens1 or not tokens2:
        return 0.0
    intersection = tokens1 & tokens2
    union = tokens1 | tokens2
    return len(intersection) / len(union)


def get_connection():
    if USE_POSTGRES:
        import psycopg2
        import psycopg2.extras
        dsn = settings.DATABASE_URL
        if dsn.startswith("postgres://"):
            dsn = "postgresql://" + dsn[len("postgres://"):]
        if "sslmode" not in dsn:
            separator = '&' if '?' in dsn else '?'
            dsn = f"{dsn}{separator}sslmode=require"
        print(f"🔌 Connecting to PostgreSQL...")
        conn = psycopg2.connect(dsn)
        conn.autocommit = False
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        return conn, cursor, True
    else:
        import sqlite3
        db_path = settings.DB_PATH
        print(f"🔌 Connecting to SQLite: {db_path}")
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        return conn, cursor, False


def backfill_pegawai():
    conn, cursor, is_pg = get_connection()

    print("📊 Step 1: Fetching pegawai_penyelaras records with empty no_kp...")
    cursor.execute("""
        SELECT id, nama_penuh FROM pegawai_penyelaras 
        WHERE (no_kp IS NULL OR no_kp = '') AND aktif = 1
        ORDER BY id
    """)
    pegawai_list = [dict(r) for r in cursor.fetchall()]
    print(f"   Found {len(pegawai_list)} officers missing IC/phone data.")
    
    if len(pegawai_list) == 0:
        print("✅ No records need backfilling. Exiting.")
        conn.close()
        return

    print("\n📊 Step 2: Fetching all pengundi records for matching...")
    cursor.execute("""
        SELECT id, no_kp, nama_penuh, no_telefon, dm 
        FROM pengundi 
        WHERE status_fizikal = 'Hidup' AND status_rekod = 'Sah'
          AND no_kp IS NOT NULL AND no_kp != ''
        ORDER BY id
    """)
    pengundi_rows = [dict(r) for r in cursor.fetchall()]
    print(f"   Loaded {len(pengundi_rows)} pengundi records for matching.")

    # Build lookup structures
    exact_lookup = {}
    pengundi_list = []
    
    for r in pengundi_rows:
        norm = normalize_name(r["nama_penuh"])
        if norm:
            exact_lookup[norm] = (r["no_kp"], r.get("no_telefon"), r.get("dm"))
            pengundi_list.append({
                "id": r["id"],
                "no_kp": r["no_kp"],
                "nama_penuh": r["nama_penuh"],
                "no_telefon": r.get("no_telefon"),
                "dm": r.get("dm"),
                "norm": norm,
                "tokens": get_tokens(r["nama_penuh"])
            })

    matched_count = 0
    partial_count = 0
    unmatched_count = 0
    now = datetime.now().isoformat()

    for pegawai in pegawai_list:
        pp_id = pegawai["id"]
        pp_name = pegawai["nama_penuh"]
        pp_norm = normalize_name(pp_name)

        matched = None
        match_type = ""

        # TIER 1: Exact match
        if pp_norm in exact_lookup:
            matched = exact_lookup[pp_norm]
            match_type = "EXACT"

        # TIER 2: Fuzzy token match >= 0.7
        if not matched:
            best_score = 0.0
            best_match = None
            best_name = ""
            for p in pengundi_list:
                score = token_similarity(pp_name, p["nama_penuh"])
                if score > best_score and score >= 0.7:
                    best_score = score
                    best_match = (p["no_kp"], p.get("no_telefon"), p.get("dm"))
                    best_name = p["nama_penuh"]
            if best_match:
                matched = best_match
                match_type = f"FUZZY({best_score:.2f} vs '{best_name}')"

        if matched:
            no_kp, no_telefon, dm = matched
            if is_pg:
                cursor.execute("""
                    UPDATE pegawai_penyelaras 
                    SET no_kp = %s, no_telefon = %s, dm = %s, dikemaskini_pada = %s
                    WHERE id = %s
                """, (no_kp, no_telefon, dm, now, pp_id))
            else:
                cursor.execute("""
                    UPDATE pegawai_penyelaras 
                    SET no_kp = ?, no_telefon = ?, dm = ?, dikemaskini_pada = ?
                    WHERE id = ?
                """, (no_kp, no_telefon, dm, now, pp_id))
            conn.commit()
            matched_count += 1
            if match_type.startswith("FUZZY"):
                partial_count += 1
            print(f"   ✅ #{pp_id} '{pp_name}' -> {match_type}: KP={no_kp}, Tel={no_telefon or '-'}")
        else:
            unmatched_count += 1
            print(f"   ⚠️  #{pp_id} '{pp_name}' -> NO MATCH")

    print(f"\n{'='*60}")
    print(f"📋 BACKFILL SUMMARY:")
    print(f"   Total processed: {len(pegawai_list)}")
    print(f"   ✅ Exact matches: {matched_count - partial_count}")
    print(f"   🔤 Fuzzy matches: {partial_count}")
    print(f"   ⚠️  No match (needs manual entry via Edit button): {unmatched_count}")
    print(f"{'='*60}")

    if unmatched_count > 0:
        print(f"\n📝 Unmatched officers requiring manual entry:")
        for pegawai in pegawai_list:
            pp_id = pegawai["id"]
            pp_name = pegawai["nama_penuh"]
            pp_norm = normalize_name(pp_name)
            is_matched = pp_norm in exact_lookup
            if not is_matched:
                for p in pengundi_list:
                    if token_similarity(pp_name, p["nama_penuh"]) >= 0.7:
                        is_matched = True
                        break
            if not is_matched:
                print(f"   - ID #{pp_id}: '{pp_name}'")

    conn.close()
    print("\n✅ Backfill complete!")


if __name__ == "__main__":
    backfill_pegawai()