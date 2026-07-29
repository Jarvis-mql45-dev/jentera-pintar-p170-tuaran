#!/usr/bin/env python3
"""
benchmark_pages.py — End-to-End Page Load Speed Benchmark
for JenteraPintar P170 Tuaran (Vanilla JS SPA)

Measures real browser rendering time for each navigation tab:
1. Papan Pemuka (Dashboard)
2. Senarai Pengundi
3. Kelulusan Data
4. Log Aktiviti
5. Pengurusan Pengguna
6. Import Data
7. Pegawai Penyelaras
8. Ketua Keluarga
9. PPU (Petunjuk Prestasi Utama / KPI)

Each page is clicked 3 times. Average, Min, Max latency reported.
"""

import asyncio
import json
import time
import sys
from datetime import datetime
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout

# ===== CONFIGURATION =====
BASE_URL = "https://jentera-pintar-p170-tuaran.vercel.app"
USERNAME = "developer"
PASSWORD = "dev123"
ITERATIONS = 3
NAV_TIMEOUT = 30000  # 30 seconds max wait per page

# ===== PAGE DEFINITIONS =====
# Each entry: (display_name, navigate_page_id, dom_ready_selector, fallback_selector)
PAGES = [
    ("Papan Pemuka", "dashboard",
     "#contentArea .stat-card",
     "#contentArea .card"),
    ("Senarai Pengundi", "pengundi",
     "#contentArea table",
     "#contentArea .table-responsive"),
    ("Kelulusan Data", "approval",
     "#contentArea table",
     "#contentArea .card"),
    ("Log Aktiviti", "audit",
     "#contentArea table",
     "#contentArea .card"),
    ("Pengurusan Pengguna", "users",
     "#contentArea table",
     "#contentArea .card"),
    ("Import Data", "import",
     "#contentArea input[type='file']",
     "#contentArea .card"),
    ("Pegawai Penyelaras", "pegawai-penyelaras",
     "#contentArea",
     "#contentArea"),
    ("Ketua Keluarga", "ketua-keluarga",
     "#contentArea",
     "#contentArea"),
    ("PPU (KPI)", "kpi",
     "#contentArea",
     "#contentArea"),
]

async def do_login(page):
    """Login to the SPA. The login form uses #loginUsername and #loginPassword."""
    print("🔑 Logging in...")
    
    # Wait for login form to render
    await page.wait_for_timeout(1500)
    
    # Fill username
    await page.fill("#loginUsername", USERNAME)
    await page.wait_for_timeout(200)
    
    # Fill password
    await page.fill("#loginPassword", PASSWORD)
    await page.wait_for_timeout(200)
    
    # Click the Log Masuk button — it has onclick calling handleLogin
    await page.click("button:has-text('Log Masuk')")
    
    # Wait for login to process and sidebar to appear
    await page.wait_for_timeout(3000)
    
    # Wait for sidebar to become visible — that means login succeeded
    try:
        await page.wait_for_selector("#sidebar:not(.hidden)", state="attached", timeout=15000)
        print("✅ Login successful — sidebar visible")
        return True
    except PlaywrightTimeout:
        print("⚠️ Sidebar not visible after login. Trying fallback...")
        return False


async def do_direct_login(page):
    """Direct API login + localStorage injection as fallback."""
    print("🔐 Attempting direct API login...")
    success = await page.evaluate("""
        async () => {
            try {
                const res = await fetch('/api/login', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({"username": "developer", "kata_laluan": "dev123"})
                });
                const data = await res.json();
                if (data.access_token) {
                    localStorage.setItem('token', data.access_token);
                    localStorage.setItem('user', JSON.stringify(data.user));
                    localStorage.setItem('currentPage', 'dashboard');
                    return { success: true, user: data.user };
                }
                return { success: false, error: data };
            } catch(e) {
                return { success: false, error: e.message };
            }
        }
    """)
    if success.get("success"):
        print(f"✅ Direct login OK — user: {success.get('user', {}).get('nama_penuh', 'unknown')}")
        await page.reload(wait_until="networkidle")
        await page.wait_for_timeout(5000)
        return True
    else:
        print(f"❌ Direct login failed: {success}")
        return False


async def measure_page_load(page, page_id: str, ready_selector: str, fallback_selector: str) -> float:
    """
    Click sidebar link, wait for page to fully render, return elapsed ms.
    Strategy:
      1. Click the sidebar button by calling navigate(page_id) in JS
      2. Wait for smooth overlay to appear (loading state)
      3. Wait for smooth overlay to disappear (data loaded)
      4. Wait for primary DOM selector to appear (table / stat-card)
      5. If primary fails, wait for fallback selector
      6. Return elapsed time from click to DOM ready
    """
    start = time.perf_counter()
    
    # Use JS to navigate (faster than finding and clicking the button)
    await page.evaluate(f"navigate('{page_id}')")
    
    # Wait for smooth overlay to appear and then disappear (loading indicator)
    try:
        await page.wait_for_selector("#smoothOverlay.active", state="attached", timeout=5000)
        await page.wait_for_selector("#smoothOverlay.active", state="detached", timeout=NAV_TIMEOUT)
    except PlaywrightTimeout:
        pass

    # Wait for the primary content selector (table / stat-cards / etc)
    try:
        await page.wait_for_selector(ready_selector, state="attached", timeout=NAV_TIMEOUT)
    except PlaywrightTimeout:
        try:
            await page.wait_for_selector(fallback_selector, state="attached", timeout=5000)
        except PlaywrightTimeout:
            pass

    # Tiny buffer for rendering to complete
    await page.wait_for_timeout(200)
    
    end = time.perf_counter()
    elapsed_ms = (end - start) * 1000
    return elapsed_ms


async def run_benchmark():
    results = {}  # page_name -> list of latencies (ms)
    
    print("=" * 80)
    print("  🏁 JENTERA PINTAR P170 TUARAN — PAGE LOAD BENCHMARK")
    print(f"  🖥️  Production URL: {BASE_URL}")
    print(f"  👤 User: {USERNAME}")
    print(f"  🔁 Iterations per page: {ITERATIONS}")
    print(f"  ⏰ Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    print()

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
            ]
        )
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            locale="ms-MY",
        )
        page = await context.new_page()

        # ===== PHASE 1: LOGIN =====
        print("📡 Connecting to production...")
        try:
            await page.goto(BASE_URL, wait_until="networkidle", timeout=45000)
            print("✅ Page loaded successfully")
        except Exception as e:
            print(f"❌ Failed to load page: {e}")
            await browser.close()
            return results

        # Try to login with form first
        logged_in = await do_login(page)
        
        if not logged_in:
            # Check if we got redirected to home page already
            try:
                sidebar_el = await page.wait_for_selector("#sidebar:not(.hidden)", state="attached", timeout=3000)
                if sidebar_el:
                    logged_in = True
            except PlaywrightTimeout:
                pass
                
        if not logged_in:
            # Fallback: direct API login
            logged_in = await do_direct_login(page)
            
        if not logged_in:
            print("❌ All login methods failed. Aborting.")
            await browser.close()
            return results

        # ===== PHASE 2: BENCHMARK EACH PAGE =====
        print("\n📊 Running benchmark...\n")
        
        for page_name, page_id, ready_sel, fallback_sel in PAGES:
            print(f"  ⏳ {page_name} ({page_id})...", end=" ", flush=True)
            
            latencies = []
            for i in range(ITERATIONS):
                try:
                    elapsed = await measure_page_load(page, page_id, ready_sel, fallback_sel)
                    latencies.append(elapsed)
                    print(f"{elapsed:.0f}ms", end=" ", flush=True)
                except Exception as e:
                    print(f"❌({e})", end=" ", flush=True)
                    latencies.append(None)
            
            results[page_name] = latencies
            valid = [l for l in latencies if l is not None]
            avg = sum(valid) / max(len(valid), 1)
            print(f"→ Avg: {avg:.0f}ms")

        await browser.close()
    
    return results


def print_summary(results: dict):
    """Print a formatted summary table of the benchmark results."""
    print()
    print("=" * 80)
    print("  📋 BENCHMARK SUMMARY — REAL PAGE LOAD SPEEDS")
    print("=" * 80)
    print(f"  Production: {BASE_URL}")
    print(f"  Timestamp:  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Iterations: {ITERATIONS} per page")
    print()
    
    # Header
    print(f"  {'#':<3} {'Halaman':<30} {'Purata':<10} {'Min':<10} {'Maks':<10} {'Status':<10}")
    print(f"  {'-'*3} {'-'*30} {'-'*10} {'-'*10} {'-'*10} {'-'*10}")
    
    total_avg = 0
    page_count = 0
    fastest = float('inf')
    fastest_page = ""
    slowest = 0
    slowest_page = ""
    
    for idx, (page_name, latencies) in enumerate(results.items(), 1):
        valid = [l for l in latencies if l is not None]
        if valid:
            avg = sum(valid) / len(valid)
            mn = min(valid)
            mx = max(valid)
            status = "✅" if avg < 5000 else "⚠️" if avg < 10000 else "❌"
            
            total_avg += avg
            page_count += 1
            if mn < fastest:
                fastest = mn
                fastest_page = page_name
            if mx > slowest:
                slowest = mx
                slowest_page = page_name
        else:
            avg = mn = mx = 0
            status = "💀"
        
        print(f"  {idx:<3} {page_name:<30} {avg:<10.0f} {mn:<10.0f} {mx:<10.0f} {status:<10}")
    
    print(f"  {'-'*3} {'-'*30} {'-'*10} {'-'*10} {'-'*10} {'-'*10}")
    overall_avg = total_avg / max(page_count, 1)
    print(f"  {'':<3} {'OVERALL AVERAGE':<30} {overall_avg:<10.0f} {'':<10} {'':<10}")
    print(f"  {'':<3} {'FASTEST PAGE':<30} {'':<10} {'':<10} {'':<10} {fastest_page:<10} ({fastest:.0f}ms)")
    print(f"  {'':<3} {'SLOWEST PAGE':<30} {'':<10} {'':<10} {'':<10} {slowest_page:<10} ({slowest:.0f}ms)")
    print()
    print("  LEGEND:")
    print("    ✅ < 5s    (Cepat — acceptable)")
    print("    ⚠️ 5-10s   (Sederhana — perlu optimisasi)")
    print("    ❌ > 10s   (Lambat — kritikal)")
    print("    💀 Gagal   (Page tidak dapat dimuat)")
    print()
    print("=" * 80)
    
    return {
        "overall_avg_ms": round(overall_avg, 1),
        "fastest_page": fastest_page,
        "fastest_ms": round(fastest, 1),
        "slowest_page": slowest_page,
        "slowest_ms": round(slowest, 1),
        "results": {
            page: {
                "latencies_ms": [round(l, 1) if l else None for l in lats],
                "avg_ms": round(sum([l for l in lats if l is not None]) / max(len([l for l in lats if l is not None]), 1), 1),
            }
            for page, lats in results.items()
        }
    }


async def main():
    print("=" * 80)
    print("  🚀 JENTERA PINTAR P170 TUARAN — PAGE LOAD BENCHMARK")
    print(f"  📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    print()
    
    results = await run_benchmark()
    
    if not results:
        print("❌ Benchmark gagal — tiada keputusan.")
        sys.exit(1)
    
    summary = print_summary(results)
    
    # Save results to JSON file
    output_file = "benchmark_results.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(f"\n📁 Full results saved to: {output_file}")
    
    # Save readable summary to txt
    txt_file = "benchmark_results.txt"
    with open(txt_file, "w", encoding="utf-8") as f:
        f.write(f"JENTERA PINTAR P170 TUARAN — PAGE LOAD BENCHMARK\n")
        f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Production: {BASE_URL}\n")
        f.write(f"Iterations: {ITERATIONS}\n\n")
        f.write(f"{'#':<3} {'Halaman':<30} {'Purata (ms)':<12} {'Min (ms)':<12} {'Maks (ms)':<12}\n")
        f.write(f"{'-'*3} {'-'*30} {'-'*12} {'-'*12} {'-'*12}\n")
        for idx, (page, lats) in enumerate(results.items(), 1):
            valid = [l for l in lats if l is not None]
            if valid:
                avg = sum(valid)/len(valid)
                mn = min(valid)
                mx = max(valid)
                f.write(f"{idx:<3} {page:<30} {avg:<12.0f} {mn:<12.0f} {mx:<12.0f}\n")
            else:
                f.write(f"{idx:<3} {page:<30} {'FAILED':<12}\n")
        f.write(f"\nOverall Average: {summary['overall_avg_ms']:.0f} ms\n")
        f.write(f"Fastest: {summary['fastest_page']} ({summary['fastest_ms']:.0f} ms)\n")
        f.write(f"Slowest: {summary['slowest_page']} ({summary['slowest_ms']:.0f} ms)\n")
    print(f"📁 Readable summary saved to: {txt_file}")


if __name__ == "__main__":
    asyncio.run(main())