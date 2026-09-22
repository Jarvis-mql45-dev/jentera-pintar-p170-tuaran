"""
check_db.py — Diagnostik sambungan pangkalan data JenteraPintar P170 Tuaran.

GUNA:
    python backend/check_db.py            # uji sambungan sahaja (BACA sahaja, tiada perubahan)
    python backend/check_db.py --init     # bina skema + seed asas (parlimen/dun/pdm) jika belum wujud
    python backend/check_db.py --selftest # ujian offline parsing DSN (tiada rangkaian)

NOTA:
  * Kata laluan TIDAK dipaparkan — hanya host/port/database/user.
  * Skrip ini tidak memadam atau mengubah data sedia ada.
  * Selepas sambungan berjaya, jalankan app sekali (uvicorn / endpoint Vercel)
    untuk seed pengguna lalai (developer/admin/petugas/ketuafamily/pemerhati).
"""
import os
import sys

# Pastikan root projek dalam sys.path supaya 'backend.*' boleh diimport
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 🛡️ POKA-YOKE: Konsol Windows (cp1252) tidak menyokong emoji → elak UnicodeEncodeError.
# Alternatif: jalankan dengan `python -X utf8 backend/check_db.py`
for _aliran in (sys.stdout, sys.stderr):
    try:
        _aliran.reconfigure(errors="backslashreplace")
    except Exception:
        pass

from backend.config import settings
from backend.database import (
    USE_POSTGRES,
    describe_database_target,
    get_db,
)

TABLES = [
    "parlimen", "dun", "pdm", "kampung",
    "pengundi", "users", "audit_logs", "approval_queue",
    "ketua_keluarga", "pegawai_penyelaras",
]


def run_selftest() -> int:
    """
    Ujian OFFLINE untuk _transform_dsn() — tiada sambungan rangkaian.
    Tujuan: pastikan parsing DSN DINAMIK (tiada project ref / host pooler di-hardcode).
    Guna: python backend/check_db.py --selftest
    """
    from urllib.parse import urlsplit
    from backend.database import _transform_dsn

    ref_lama = "hgweacgibbnynjviocje"          # ref yang hilang (hanya sebagai Data ujian)
    ref_baru = "newprojectref000001"           # ref rekaan untuk ujian

    kunci_env = ("JENTERA_SUPABASE_REF", "JENTERA_DB_HOST", "JENTERA_DB_PORT")
    env_asal = {k: os.environ.get(k) for k in kunci_env}

    def reset_env():
        for k, v in env_asal.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    kes = [
        {
            "nama": "DSN pooler lama (ref dalam username) — kekal sama, tiada rewrite",
            "dsn": f"postgresql://postgres.{ref_lama}:PWD@aws-0-ap-southeast-1.pooler.supabase.com:6543/postgres?sslmode=require",
            "env": {},
            "expect": {"host": "aws-0-ap-southeast-1.pooler.supabase.com", "user": f"postgres.{ref_lama}", "port": 6543, "query": "sslmode=require"},
            "same": True,
        },
        {
            "nama": "Pooler cluster LAIN (aws-1) + ref dalam username — tiada host swap",
            "dsn": f"postgresql://postgres.{ref_baru}:PWD@aws-1-ap-southeast-1.pooler.supabase.com:5432/postgres",
            "env": {},
            "expect": {"host": "aws-1-ap-southeast-1.pooler.supabase.com", "user": f"postgres.{ref_baru}", "port": 5432, "query": ""},
            "same": True,
        },
        {
            "nama": "Pooler username TANPA ref + JENTERA_SUPABASE_REF (auto-lengkap)",
            "dsn": "postgresql://postgres:PWD@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres",
            "env": {"JENTERA_SUPABASE_REF": ref_baru},
            "expect": {"host": "aws-1-ap-southeast-1.pooler.supabase.com", "user": f"postgres.{ref_baru}", "port": 6543, "query": ""},
        },
        {
            "nama": "Sambungan DIRECT db.<ref>.supabase.co — TIDAK ditukar ke aws-0 (regresi)",
            "dsn": f"postgresql://postgres:PWD@db.{ref_baru}.supabase.co:5432/postgres",
            "env": {},
            "expect": {"host": f"db.{ref_baru}.supabase.co", "user": "postgres", "port": 5432, "query": ""},
            "same": True,
        },
        {
            "nama": "Dialect postgres:// → postgresql://",
            "dsn": "postgres://postgres:PWD@localhost:5432/pengundi",
            "env": {},
            "expect": {"host": "localhost", "user": "postgres", "port": 5432, "query": ""},
        },
        {
            "nama": "Override host/port melalui env (JENTERA_DB_HOST / JENTERA_DB_PORT)",
            "dsn": "postgresql://postgres:PWD@host-lama.example.com:5432/postgres",
            "env": {"JENTERA_DB_HOST": "db.example.com", "JENTERA_DB_PORT": "6543"},
            "expect": {"host": "db.example.com", "user": "postgres", "port": 6543, "query": ""},
        },
        {
            "nama": "DATABASE_URL kosong → ValueError",
            "dsn": "   ",
            "env": {},
            "expect_error": True,
        },
    ]

    print("=" * 72)
    print(" SELFTEST _transform_dsn() — TIADA hardcode ref/host (offline)")
    print("=" * 72)
    gagal = 0
    for k in kes:
        reset_env()
        os.environ.update(k["env"])
        hasil, ralat = None, None
        try:
            hasil = _transform_dsn(k["dsn"])
        except Exception as e:      # noqa: BLE001 - diagnostik
            ralat = e

        if k.get("expect_error"):
            ok = isinstance(ralat, ValueError)
        else:
            exp = k["expect"]
            p = urlsplit(hasil or "")
            ok = (
                ralat is None
                and p.hostname == exp["host"]
                and p.username == exp["user"]
                and (p.port or 5432) == exp["port"]
                and p.query == exp["query"]
            )
            if k.get("same"):
                ok = ok and hasil == k["dsn"]

        gagal += 0 if ok else 1
        print(f"{'✅ PASS' if ok else '❌ FAIL'} | {k['nama']}")
        if not ok and ralat is not None and not k.get("expect_error"):
            print(f"        ralat: {type(ralat).__name__}: {ralat}")
        # Bukti tiada hardcode ref lama di dalam kod
    reset_env()

    import inspect
    src = inspect.getsource(_transform_dsn)
    for terlarang in ("hgweacgibbnynjviocje", "aws-0-ap-southeast-1"):
        if terlarang in src:
            print(f"❌ FAIL | Hardcode '{terlarang}' masih ada dalam _transform_dsn()")
            gagal += 1
    if gagal == 0:
        print("\n🎉 SEMUA SELFTEST LULUS — parsing DSN 100% dinamik, tiada hardcode host/ref.")
    else:
        print(f"\n⚠️ {gagal} ujian gagal — sila semak semula _transform_dsn().")
    print("=" * 72)
    return 1 if gagal else 0


def _hint(err: Exception) -> None:
    """Cadangan tindakan berdasarkan jenis ralat — elak buang masa mengejar punca salah."""
    msg = str(err)
    if "ENOTFOUND" in msg or "tenant/user" in msg:
        print(
            "\n💡 DIAGNOSIS: Supavisor (pooler Supabase) TIDAK dapat padankan host + username "
            "kepada projek.\n"
            "   Maksudnya: host cluster pooler salah (aws-0/aws-1/aws-2 berbeza mengikut projek) "
            "ATAU projek Supabase sudah dipadam/dipause.\n"
            "   TINDAKAN: Buka Supabase Dashboard → projek → Connect → Transaction/Session pooler, "
            "salin SEMULA connection string penuh (jangan reka host sendiri), "
            "kemas kini DATABASE_URL."
        )
    elif "could not translate host name" in msg or "Name or service not known" in msg:
        print("\n💡 DIAGNOSIS: Hostname tidak wujud lagi (DNS gagal) — projek Supabase kemungkinan "
              "sudah dipadam atau host salah taip.")
    elif "password authentication failed" in msg:
        print("\n💡 DIAGNOSIS: Password/kata laluan DB salah (host betul). Reset password di "
              "Supabase → Settings → Database, kemudian kemas kini DATABASE_URL.")
    elif "sslmode" in msg or "SSL" in msg:
        print("\n💡 DIAGNOSIS: Isu SSL — tambah '?sslmode=require' pada DATABASE_URL.")
    elif "timed out" in msg or "timeout" in msg:
        print("\n💡 DIAGNOSIS: Timeout — semak sama ada projek Supabase dipause atau rangkaian "
              "menghalang port 5432/6543.")
    print()


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)

    if "--selftest" in argv:
        return run_selftest()

    run_init = "--init" in argv

    print("=" * 72)
    print(" DIAGNOSTIK PANGKALAN DATA — JENTERA PINTAR P170 TUARAN")
    print("=" * 72)
    print(f"Mod pangkalan data : {'PostgreSQL (DATABASE_URL)' if USE_POSTGRES else 'SQLite tempatan'}")
    print(f"Mod production     : {settings.PRODUCTION}")
    print(f"Sasaran            : {describe_database_target()}")
    print("-" * 72)

    if run_init:
        try:
            from backend.database import init_db
            print("🔧 Menjalankan init_db() — bina skema + seed parlimen/dun/pdm...")
            init_db()
        except Exception as e:
            print(f"❌ init_db() gagal: {type(e).__name__}: {e}")

    db = None
    try:
        db = get_db()
    except Exception as e:
        print(f"\n❌ SAMBUNGAN GAGAL: {type(e).__name__}: {e}")
        _hint(e)
        return 1

    print("\n✅ SAMBUNGAN DB BERJAYA")
    cursor = db.cursor()
    for table in TABLES:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            row = cursor.fetchone()
            jumlah = row[0] if row else "?"
            print(f"   {table:<20} : {jumlah} baris")
        except Exception as e:
            print(f"   {table:<20} : ⚠️ tidak dapat dibaca ({type(e).__name__})")
    try:
        db.close()
    except Exception:
        pass
    print("-" * 72)
    print("💡 Jika jadual 0 baris: buka app sekali supaya pengguna lalai di-seed, "
          "kemudian import data pengundi sebenar melalui menu Import Excel.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
