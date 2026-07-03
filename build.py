"""
Build Script untuk JenteraPintar N05 Matunggong
==============================================
Fungsi:
1. Minify HTML, CSS, dan JavaScript
2. Obfuscate JavaScript kritikal (logik perniagaan)
3. Buang semua source maps
4. Salin ke folder dist/ untuk production
5. Sembunyikan kod sumber asal dari frontend

Penggunaan:
    python build.py              # Build untuk production
    python build.py --dev        # Build untuk development (tanpa obfuscation)
    python build.py --serve      # Build dan run backend

Keperluan:
    pip install html-minifier-terser javascript-obfuscator csscompressor
"""

import os
import shutil
import sys
import re
import json
import subprocess
import tempfile
from datetime import datetime

# ============================
# KONFIGURASI
# ============================
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(PROJECT_DIR, 'frontend')
BACKEND_DIR = os.path.join(PROJECT_DIR, 'backend')
DIST_DIR = os.path.join(PROJECT_DIR, 'frontend', 'dist')
BACKUP_DIR = os.path.join(PROJECT_DIR, 'frontend', 'src_backup')

VERSION = "1.1.0"
BUILD_TIME = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# Fail-fail yang akan diproses
FILES_TO_PROCESS = {
    'html': ['index.html'],
    'js': [],  # JS inline dalam HTML - akan diekstrak
    'css': [], # CSS inline dalam HTML - akan diekstrak
    'static': [
        'manifest.json',
        'service-worker.js',
        'icons/'
    ]
}


def get_npx_path():
    """Cari path npx dalam sistem (Windows/Linux/Mac)."""
    possible_paths = []
    
    # Check common npm global paths
    npm_root = subprocess.run(["npm", "root", "-g"], capture_output=True, text=True, timeout=10)
    if npm_root.returncode == 0:
        npm_global = npm_root.stdout.strip()
        # npx biasanya dalam folder yang sama dengan npm
        possible_paths.append(npm_global)
        
        # Bin folder (Linux/Mac)
        bin_dir = os.path.join(os.path.dirname(npm_global), 'bin')
        if os.path.exists(bin_dir):
            possible_paths.append(bin_dir)
        
        # npm prefix
        npm_prefix = subprocess.run(["npm", "prefix", "-g"], capture_output=True, text=True, timeout=10)
        if npm_prefix.returncode == 0:
            prefix = npm_prefix.stdout.strip()
            
            # Windows: AppData/Roaming/npm
            win_npm = os.path.join(prefix, 'npm')
            if os.path.exists(win_npm):
                possible_paths.append(prefix)
    
    # Check Windows specific paths
    appdata = os.environ.get('APPDATA', '')
    if appdata:
        npm_dir = os.path.join(appdata, 'npm')
        if os.path.exists(npm_dir):
            possible_paths.append(npm_dir)
    
    # Check if npx is in PATH
    for path_dir in os.environ.get('PATH', '').split(os.pathsep):
        npx_path = os.path.join(path_dir, 'npx')
        npx_path_cmd = os.path.join(path_dir, 'npx.cmd')
        if os.path.exists(npx_path) and npx_path not in possible_paths:
            possible_paths.append(path_dir)
        if os.path.exists(npx_path_cmd) and path_dir not in possible_paths:
            possible_paths.append(path_dir)
    
    return possible_paths


def find_executable(name, search_paths):
    """Cari executable dalam senarai paths."""
    for path_dir in search_paths:
        for ext in ['', '.cmd', '.bat', '.exe', '.ps1']:
            exe_path = os.path.join(path_dir, f"{name}{ext}")
            if os.path.exists(exe_path):
                return exe_path
    return name  # Return name as fallback (hope PATH has it)


def run_shell_cmd(cmd_parts, input_data=None):
    """Run a command via shell (for .cmd files on Windows)."""
    npm_path = r"C:\Users\Admin\AppData\Roaming\npm"
    env = os.environ.copy()
    env['PATH'] = npm_path + os.pathsep + env.get('PATH', '')
    env['PYTHONIOENCODING'] = 'utf-8'
    
    cmd_str = ' '.join(cmd_parts) if isinstance(cmd_parts, list) else cmd_parts
    
    try:
        if input_data is not None:
            # For stdin mode - write to temp file instead of pipe
            with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False, encoding='utf-8') as f:
                f.write(input_data)
                temp_stdin = f.name
            
            result = subprocess.run(
                f'{cmd_str} < "{temp_stdin}"',
                capture_output=True,
                text=True,
                timeout=120,
                env=env,
                shell=True
            )
            try:
                os.unlink(temp_stdin)
            except:
                pass
            return result
        else:
            result = subprocess.run(
                cmd_str,
                capture_output=True,
                text=True,
                timeout=120,
                env=env,
                shell=True
            )
            return result
    except subprocess.TimeoutExpired as e:
        raise e
    except Exception as e:
        raise FileNotFoundError(f"Command failed: {cmd_str[:100]}... Error: {e}")


def check_dependencies():
    """Semak sama ada alat-alat yang diperlukan telah dipasang."""
    tools_ok = True
    
    npm_bin = r"C:\Users\Admin\AppData\Roaming\npm"
    
    # Check terser
    terser_path = os.path.join(npm_bin, "terser.cmd")
    if os.path.exists(terser_path):
        print(f"  ✅ terser (JS minifier) tersedia di {terser_path}")
    else:
        print("  ⚠️  terser tidak dijumpai. Guna regex fallback.")
        tools_ok = False
    
    # Check javascript-obfuscator
    obf_path = os.path.join(npm_bin, "javascript-obfuscator.cmd")
    if os.path.exists(obf_path):
        print(f"  ✅ javascript-obfuscator tersedia di {obf_path}")
    else:
        print("  ⚠️  javascript-obfuscator tidak dijumpai.")
        tools_ok = False
    
    return tools_ok


def _powershell_exec(ps_script):
    """Execute PowerShell script and return result."""
    ps_cmd = ['powershell', '-NoProfile', '-Command', ps_script]
    result = subprocess.run(
        ps_cmd,
        capture_output=True,
        text=True,
        timeout=120
    )
    return result


def minify_js_with_terser(js_code: str) -> str:
    """Minify JavaScript menggunakan Terser CLI via PowerShell."""
    try:
        terser_path = r"C:\Users\Admin\AppData\Roaming\npm\terser.cmd"
        
        # Write input to temp file to avoid Unicode encoding issues
        with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False, encoding='utf-8') as f:
            f.write(js_code)
            temp_input = f.name
        
        # Use PowerShell to pipe the file through terser
        ps_cmd = f'Get-Content "{temp_input}" -Raw | & "{terser_path}" --compress passes=2 --mangle toplevel=true --comments "/^!/" --format max_line_len=500'
        
        result = _powershell_exec(ps_cmd)
        
        try:
            os.unlink(temp_input)
        except:
            pass
        
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except Exception as e:
        print(f"     ⚠️  terser gagal: {e}")
    
    # Fallback: regex minification
    return fallback_minify_js(js_code)


def obfuscate_js(js_code: str) -> str:
    """Obfuscate JavaScript menggunakan javascript-obfuscator CLI via PowerShell."""
    try:
        obf_path = r"C:\Users\Admin\AppData\Roaming\npm\javascript-obfuscator.cmd"
        
        # Tulis ke temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False, encoding='utf-8') as f:
            f.write(js_code)
            temp_input = f.name
        
        temp_output = temp_input + '.obfuscated.js'
        
        # Use PowerShell to execute the .cmd with proper args
        ps_cmd = (
            f'& "{obf_path}" "{temp_input}" '
            f'--output "{temp_output}" '
            f'--compact true '
            f'--control-flow-flattening true '
            f'--control-flow-flattening-threshold 0.75 '
            f'--numbers-to-expressions true '
            f'--simplify true '
            f'--shuffle-string-array true '
            f'--split-strings true '
            f'--string-array-threshold 0.75 '
            f'--string-array-encoding base64 '
            f'--unicode-escape-sequence false '
            f'--disable-console-output false '
            f'--debug-protection false '
            f'--source-map false'
        )
        
        result = _powershell_exec(ps_cmd)
        
        if result.returncode == 0 and os.path.exists(temp_output):
            with open(temp_output, 'r', encoding='utf-8') as f:
                obfuscated = f.read()
            # Cleanup
            try:
                os.unlink(temp_input)
                if os.path.exists(temp_output):
                    os.unlink(temp_output)
            except:
                pass
            if obfuscated.strip():
                return obfuscated.strip()
        
        # Cleanup on failure
        try:
            os.unlink(temp_input)
            if os.path.exists(temp_output):
                os.unlink(temp_output)
        except:
            pass
            
    except Exception as e:
        print(f"     ⚠️  obfuscation gagal: {e}")
    
    # Fallback: minify instead
    print("     ⚠️  Obfuscation gagal, guna minify sebagai ganti")
    return minify_js_with_terser(js_code)


def fallback_minify_js(js_code: str) -> str:
    """Fallback: regex-based JS minification."""
    # Buang comments
    js_code = re.sub(r'//.*', '', js_code)
    js_code = re.sub(r'/\*.*?\*/', '', js_code, flags=re.DOTALL)
    # Buang whitespace
    js_code = re.sub(r'\s+', ' ', js_code)
    js_code = re.sub(r'\s*([{}\[\];,:\(\)\+\-\*/%])\s*', r'\1', js_code)
    return js_code.strip()


def extract_inline_css(html_content):
    """Ekstrak CSS dari <style> tag untuk minification."""
    pattern = re.compile(r'<style>(.*?)</style>', re.DOTALL | re.IGNORECASE)
    
    def replace_css(match):
        css_code = match.group(1)
        # CSS Minification via regex
        # Buang comments
        css_code = re.sub(r'/\*.*?\*/', '', css_code, flags=re.DOTALL)
        # Buang whitespace di sekeliling simbol
        css_code = re.sub(r'\s*([{}:;,])\s*', r'\1', css_code)
        # Buang whitespace sebelum/lepas kurungan
        css_code = re.sub(r'\s*{\s*', '{', css_code)
        css_code = re.sub(r'\s*}\s*', '}', css_code)
        # Buang whitespace dalam properties
        css_code = re.sub(r':\s+', ':', css_code)
        css_code = re.sub(r',\s+', ',', css_code)
        # Buang last semicolon before }
        css_code = re.sub(r';}', '}', css_code)
        # Buang unit 0px jadi 0
        css_code = re.sub(r'\b0px\b', '0', css_code)
        # Buang leading/trailing whitespace
        css_code = css_code.strip()
        
        return f'<style>{css_code}</style>'
    
    return pattern.sub(replace_css, html_content)


def extract_inline_js(html_content, obfuscate=False):
    """Ekstrak JS dari <script> tags untuk minification/obfuscation."""
    # Jangan sentuh external script (src=...)
    pattern = re.compile(
        r'<script\b(?![^>]*\bsrc\s*=)([^>]*)>(.*?)</script>',
        re.DOTALL | re.IGNORECASE
    )
    
    def replace_js(match):
        attributes = match.group(1)
        js_code = match.group(2)
        
        if not js_code.strip():
            return match.group(0)
        
        # Jangan obfuscate tailwind config atau service worker registration
        if 'tailwind.config' in js_code:
            # Minify saja
            return f'<script{attributes}>{fallback_minify_js(js_code)}</script>'
        
        # Obfuscate + Minify untuk logik kritikal
        if obfuscate:
            print(f"     🔒 Obfuscating JavaScript ({len(js_code):,} chars)...")
            js_minified = obfuscate_js(js_code)
        else:
            # Minify saja
            print(f"     ⚡ Minifying JavaScript ({len(js_code):,} chars)...")
            js_minified = minify_js_with_terser(js_code)
        
        return f'<script{attributes}>{js_minified}</script>'
    
    return pattern.sub(replace_js, html_content)


def obfuscate_service_worker(sw_path, dist_sw_path):
    """Obfuscate service-worker.js untuk production."""
    if not os.path.exists(sw_path):
        return
    
    print("  📦 Memproses service-worker.js...")
    with open(sw_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    obfuscated = obfuscate_js(content)
    
    with open(dist_sw_path, 'w', encoding='utf-8') as f:
        f.write(obfuscated)
    print(f"  ✅ service-worker.js diobfuscate ({len(obfuscated):,} chars)")


def process_html(file_path, obfuscate=False):
    """Process HTML file: extract/minify CSS, minify/obfuscate JS."""
    print(f"\n  📄 Memproses: {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_size = len(content)
    print(f"     Saiz asal: {original_size:,} bytes")
    
    # 1. Minify CSS inline
    print("     🎨 Memampatkan CSS...")
    content = extract_inline_css(content)
    
    # 2. Minify/Obfuscate JS inline
    print(f"     ⚡ Memampatkan JavaScript{' + obfuscation' if obfuscate else ''}...")
    content = extract_inline_js(content, obfuscate=obfuscate)
    
    # 3. Buang HTML comments (kecuali conditional IE)
    content = re.sub(r'<!--(?!\[if).*?-->', '', content, flags=re.DOTALL)
    
    # 4. Minify HTML menggunakan regex (tanpa html-minifier-terser yang mungkin fail)
    # Buang whitespace berlebihan
    content = re.sub(r'>\s+<', '>\n<', content)  # Preserve newlines between tags
    content = re.sub(r'\n\s*\n', '\n', content)  # Buang empty lines
    content = re.sub(r'^\s+', '', content, flags=re.MULTILINE)  # Buang leading whitespace
    content = re.sub(r'\s+$', '', content, flags=re.MULTILINE)  # Buang trailing whitespace
    
    new_size = len(content)
    savings = ((original_size - new_size) / original_size) * 100
    print(f"     ✅ Saiz akhir: {new_size:,} bytes (jimat {savings:.1f}%)")
    
    return content


def copy_static_files(dist_dir):
    """Salin fail statik yang tidak perlu diproses."""
    print("\n  📁 Menyalin fail statik...")
    
    # Copy manifest.json
    manifest_src = os.path.join(FRONTEND_DIR, 'manifest.json')
    if os.path.exists(manifest_src):
        shutil.copy2(manifest_src, os.path.join(dist_dir, 'manifest.json'))
        print("  ✅ manifest.json disalin")
    
    # Copy icons directory
    icons_src = os.path.join(FRONTEND_DIR, 'icons')
    icons_dst = os.path.join(dist_dir, 'icons')
    if os.path.exists(icons_src):
        if os.path.exists(icons_dst):
            shutil.rmtree(icons_dst)
        shutil.copytree(icons_src, icons_dst)
        print("  ✅ icons/ disalin")
    
    # Copy service worker (akan diobfuscate nanti)
    sw_src = os.path.join(FRONTEND_DIR, 'service-worker.js')
    sw_dst = os.path.join(dist_dir, 'service-worker.js')
    if os.path.exists(sw_src):
        shutil.copy2(sw_src, sw_dst)
        print("  ✅ service-worker.js disalin (akan diobfuscate)")


def create_build_info(dist_dir):
    """Cipta fail build_info.json dalam dist/."""
    info = {
        "app": "JenteraPintar N05 Matunggong",
        "version": VERSION,
        "build_time": BUILD_TIME,
        "mode": "PRODUCTION",
        "notice": "Fail ini adalah hasil build untuk production. Kod sumber asal tidak disertakan.",
        "hak_cipta": "Jarvis_KM. Dilarang menyalin atau mengedar tanpa kebenaran."
    }
    info_path = os.path.join(dist_dir, 'build_info.json')
    with open(info_path, 'w', encoding='utf-8') as f:
        json.dump(info, f, indent=2, ensure_ascii=False)
    print(f"  ℹ️  build_info.json dicipta")


def create_robots_txt(dist_dir):
    """Cipta robots.txt untuk block crawlers daripada melihat fail sensitif."""
    robots_content = """# Robots.txt untuk JenteraPintar N05 Matunggong
# Dilarang mengakses fail konfigurasi/sumber

User-agent: *
Disallow: /src_backup/
Disallow: /*.map$
Disallow: /*.config.*
Disallow: /build_info.json
Allow: /
"""
    robots_path = os.path.join(dist_dir, 'robots.txt')
    with open(robots_path, 'w', encoding='utf-8') as f:
        f.write(robots_content)
    print(f"  🤖 robots.txt dicipta")


def verify_no_source_maps(dist_dir):
    """Pastikan tiada source maps dalam dist/."""
    print("\n  🔍 Memeriksa source maps...")
    found_maps = []
    for root, dirs, files in os.walk(dist_dir):
        for file in files:
            if file.endswith('.map'):
                found_maps.append(os.path.join(root, file))
    
    if found_maps:
        print(f"  ⚠️  Dijumpai {len(found_maps)} source map - MEMADAMKAN...")
        for f in found_maps:
            os.remove(f)
            print(f"     ✕ Dipadam: {f}")
    else:
        print("  ✅ Tiada source maps dijumpai")


def create_htaccess(dist_dir):
    """Cipta .htaccess untuk Apache (jika guna) - blok akses fail sensitif."""
    htaccess_content = """# Apache configuration for JenteraPintar N05 Matunggong
# Melindungi fail sensitif daripada akses awam

# Block access to source maps
<FilesMatch "\\.map$">
    Require all denied
</FilesMatch>

# Block access to backup directories
RedirectMatch 404 /\\.git(/|$)
RedirectMatch 404 /src_backup(/|$)

# Block access to config files
<FilesMatch "(config\\.py|auth\\.py|database\\.py)$">
    Require all denied
</FilesMatch>

# Block access to .py files in general
<FilesMatch "\\.py$">
    Require all denied
</FilesMatch>

# Block access to database file
<FilesMatch "pengundi\\.db$">
    Require all denied
</FilesMatch>

# Disable directory browsing
Options -Indexes

# Security headers
<IfModule mod_headers.c>
    Header always set X-Content-Type-Options "nosniff"
    Header always set X-Frame-Options "DENY"
    Header always set X-XSS-Protection "1; mode=block"
    Header always set Referrer-Policy "strict-origin-when-cross-origin"
</IfModule>

# Cache control for static assets
<FilesMatch "\\.(ico|jpg|jpeg|png|gif|svg|webp)$">
    Header set Cache-Control "public, max-age=31536000, immutable"
</FilesMatch>
<FilesMatch "\\.(css|js)$">
    Header set Cache-Control "public, max-age=86400"
</FilesMatch>
"""
    htaccess_path = os.path.join(dist_dir, '.htaccess')
    with open(htaccess_path, 'w', encoding='utf-8') as f:
        f.write(htaccess_content)
    print(f"  🛡️  .htaccess dicipta (Apache protection)")


def create_webconfig(dist_dir):
    """Cipta web.config untuk IIS (jika guna) - blok akses fail sensitif."""
    webconfig_content = """<?xml version="1.0" encoding="UTF-8"?>
<configuration>
  <system.webServer>
    <directoryBrowse enabled="false" />
    <staticContent>
      <mimeMap fileExtension=".json" mimeType="application/json" />
      <remove fileExtension=".map" />
    </staticContent>
    
    <!-- Block access to sensitive files -->
    <security>
      <requestFiltering>
        <denyUrlSequences>
          <add sequence=".map" />
          <add sequence=".py" />
          <add sequence=".db" />
          <add sequence="src_backup" />
          <add sequence=".git" />
        </denyUrlSequences>
      </requestFiltering>
    </security>
    
    <!-- Security headers -->
    <httpProtocol>
      <customHeaders>
        <add name="X-Content-Type-Options" value="nosniff" />
        <add name="X-Frame-Options" value="DENY" />
        <add name="X-XSS-Protection" value="1; mode=block" />
        <add name="Referrer-Policy" value="strict-origin-when-cross-origin" />
      </customHeaders>
    </httpProtocol>
    
    <!-- URL Rewrite for SPA routing -->
    <rewrite>
      <rules>
        <rule name="API Routes" stopProcessing="true">
          <match url="^api/.*" />
          <action type="None" />
        </rule>
      </rules>
    </rewrite>
  </system.webServer>
</configuration>"""
    webconfig_path = os.path.join(dist_dir, 'web.config')
    with open(webconfig_path, 'w', encoding='utf-8') as f:
        f.write(webconfig_content)
    print(f"  🛡️  web.config dicipta (IIS protection)")


def build(obfuscate=True):
    """Main build function."""
    print("=" * 60)
    print(f"  🔨 BUILD JENTERA PINTAR N05 MATUNGGONG")
    print(f"  Versi: {VERSION}")
    print(f"  Masa: {BUILD_TIME}")
    print(f"  Mode: {'PRODUCTION (obfuscated)' if obfuscate else 'DEVELOPMENT (minified only)'}")
    print("=" * 60)
    
    # 1. Bersihkan folder dist/
    if os.path.exists(DIST_DIR):
        print(f"\n  🧹 Membersihkan {DIST_DIR}...")
        shutil.rmtree(DIST_DIR)
    os.makedirs(DIST_DIR, exist_ok=True)
    
    # 2. Backup index.html asal (untuk rujukan)
    index_src = os.path.join(FRONTEND_DIR, 'index.html')
    if os.path.exists(index_src):
        os.makedirs(BACKUP_DIR, exist_ok=True)
        backup_path = os.path.join(BACKUP_DIR, 'index.html.backup')
        shutil.copy2(index_src, backup_path)
        print(f"\n  💾 Backup index.html -> {backup_path}")
    
    # 3. Process index.html
    print(f"\n  📝 Memproses index.html...")
    processed_html = process_html(index_src, obfuscate=obfuscate)
    
    # 4. Tulis index.html yang telah diproses ke dist/
    dist_index = os.path.join(DIST_DIR, 'index.html')
    with open(dist_index, 'w', encoding='utf-8') as f:
        f.write(processed_html)
    
    # 5. Copy static files
    copy_static_files(DIST_DIR)
    
    # 6. Obfuscate service worker
    sw_src = os.path.join(FRONTEND_DIR, 'service-worker.js')
    sw_dst = os.path.join(DIST_DIR, 'service-worker.js')
    if obfuscate and os.path.exists(sw_src):
        obfuscate_service_worker(sw_src, sw_dst)
    
    # 7. Cipta fail keselamatan
    create_build_info(DIST_DIR)
    create_robots_txt(DIST_DIR)
    create_htaccess(DIST_DIR)
    create_webconfig(DIST_DIR)
    
    # 8. Verifikasi tiada source maps
    verify_no_source_maps(DIST_DIR)
    
    # 9. Buang backup directory dari dist (jika tersalin)
    dist_backup = os.path.join(DIST_DIR, 'src_backup')
    if os.path.exists(dist_backup):
        shutil.rmtree(dist_backup)
    
    # 10. Kira saiz akhir
    total_size = 0
    file_count = 0
    for root, dirs, files in os.walk(DIST_DIR):
        for file in files:
            filepath = os.path.join(root, file)
            total_size += os.path.getsize(filepath)
            file_count += 1
    
    print("\n" + "=" * 60)
    print(f"  ✅ BUILD SELESAI!")
    print(f"  📂 Output: {DIST_DIR}")
    print(f"  📊 Fail: {file_count} fail, {total_size / 1024:.1f} KB")
    print(f"  🔒 Obfuscation: {'AKTIF' if obfuscate else 'TIDAK AKTIF'}")
    print(f"  🗺️  Source maps: DIPADAMKAN")
    print("=" * 60)
    
    print(f"""
  📋 NOTA UNTUK PRODUCTION:
  -------------------------
  1. Set environment variables:
     set JENTERA_PRODUCTION=true
     set JENTERA_SECRET_KEY=<kunci-kuat-rawak>
     set JENTERA_ALLOWED_ORIGINS=https://domain-anda.com
     set JENTERA_STATIC_DIR={DIST_DIR}
  
  2. Jalankan backend:
     cd backend && python main.py
  
  3. Aplikasi akan serve dari {DIST_DIR}
     dengan semua logik dilindungi.
  
  4. Untuk deployment VPS/cloud, rujuk DEPLOYMENT.md
  """)


if __name__ == "__main__":
    args = sys.argv[1:]
    
    if "--dev" in args:
        build(obfuscate=False)
    elif "--serve" in args:
        build(obfuscate=True)
        print("\n  🚀 Memulakan server backend...")
        os.chdir(BACKEND_DIR)
        subprocess.run([sys.executable, "main.py"])
    else:
        build(obfuscate=True)