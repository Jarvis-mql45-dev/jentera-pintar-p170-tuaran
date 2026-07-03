"""
Environment variable loader untuk JenteraPintar N05 Matunggong.
Membaca .env file untuk production configuration.
"""

import os
import sys

# Path ke .env file (root projek)
ENV_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')


def load_env_file(env_path: str = ENV_PATH) -> bool:
    """
    Load .env file ke environment variables.
    Returns True jika berjaya, False jika fail tidak wujud.
    """
    if not os.path.exists(env_path):
        print(f"ℹ️  .env file tidak dijumpai di {env_path}")
        print("   Guna config development lalai.")
        return False

    print(f"📂 Membaca konfigurasi dari {env_path}")
    loaded_count = 0
    with open(env_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()

            # Buang komen dan baris kosong
            if not line or line.startswith('#') or line.startswith('//'):
                continue

            # Parse KEY=VALUE
            if '=' in line:
                key, _, value = line.partition('=')
                key = key.strip()
                value = value.strip()

                # Buang quote jika ada
                if (value.startswith('"') and value.endswith('"')) or \
                   (value.startswith("'") and value.endswith("'")):
                    value = value[1:-1]

                # Set environment variable
                os.environ[key] = value
                loaded_count += 1

    print(f"✅ {loaded_count} pembolehubah persekitaran dimuatkan")
    return True


def ensure_production_config():
    """
    Pastikan konfigurasi production lengkap.
    Panggil sebelum app start.
    """
    # Cuba load .env
    load_env_file()

    # Dalam production, pastikan SECRET_KEY tidak menggunakan nilai lalai
    if os.environ.get("JENTERA_PRODUCTION", "").lower() == "true":
        secret_key = os.environ.get("JENTERA_SECRET_KEY", "")
        default_key = "kunci-rahasia-dun-matunggong-2026"

        if not secret_key or secret_key == default_key:
            print("=" * 60)
            print("  ⚠️  AMARAN KESELAMATAN!")
            print("  JENTERA_SECRET_KEY masih menggunakan nilai lalai!")
            print("  Sila set JENTERA_SECRET_KEY dalam .env dengan kunci rawak.")
            print("=" * 60)
            print()

        # Pastikan allowed origins di set
        origins = os.environ.get("JENTERA_ALLOWED_ORIGINS", "")
        if not origins:
            print("  ⚠️  AMARAN: JENTERA_ALLOWED_ORIGINS tidak diset!")
            print("  CORS akan menggunakan '*', yang TIDAK SELAMAT untuk production.")
            print()


# Auto-load apabila module diimport
if __name__ != "__main__":
    load_env_file()