#!/usr/bin/env python3
"""
benchmark_warm_cache.py — Cold-Start vs Warm-Cache Dashboard Speed Benchmark
for JenteraPintar P170 Tuaran (Vanilla JS SPA)

Measures Dashboard load time under two conditions:
  1. COLD: First dashboard visit after fresh login (no cached DOM/state)
  2. WARM: Dashboard visit after navigating away to Senarai Pengundi and back
     (simulates real user returning to Dashboard, leveraging in-memory cache)

Proves the <50ms UX improvement from Phase 3 cache/performance optimisations.
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
ITERATIONS = 3  # Number of Cold→Warm paired cycles
NAV_TIMEOUT = 30000
WARMUP_PAGE = "pengundi"  # Navigate here between Cold & Warm measurements

# ===== LOGIN (same proven strategy from benchmark_pages.py) =====

async def do_login(page):
    """Login via form fill."""
    print("  🔑 Logging in...")
    await page.wait_for_timeout(1500)
    await page.fill("#loginUsername", USERNAME)
    await page.wait_for_timeout(200)
    await page.fill("#loginPassword", PASSWORD)
    await page.wait_for_timeout(200)
    await page.click("button:has-text('Log Masuk')")
    await page.wait_for_timeout(3000)
    try:
        await page.wait_for_selector("#sidebar:not(.hidden)", state="attached", timeout=15000)
        print("  ✅ Login successful — sidebar visible")
        return True
    except PlaywrightTimeout:
        print("  ⚠️ Sidebar not visible after form login. Trying fallback...")
        return False


async def do_direct_login(page):
    """Direct API login + localStorage injection."""
    print("  🔐 Attempting direct API login...")
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
        print(f"  ✅ Direct login OK — user: {success.get('user', {}).get('nama_penuh', 'unknown')}")
        # Reload with 'load' instead of 'networkidle' to avoid long-polling timeout
        await page.reload(wait_until="load", timeout=30000)
        await page.wait_for_timeout(3000)
        return True
    else:
        print(f"  ❌ Direct login failed: {success}")
        return False


async def authenticate(page):
    """Complete login pipeline — form first, API fallback."""
    logged_in = await do_login(page)
    if not logged_in:
        try:
            sidebar_el = await page.wait_for_selector("#sidebar:not(.hidden)", state="attached", timeout=3000)
            if sidebar_el:
                logged_in = True
        except PlaywrightTimeout:
            pass
    if not logged_in:
        logged_in = await do_direct_login(page)
    return logged_in


async def navigate_and_wait(page, page_id: str, ready_selector: str = "#contentArea .stat-card",
                            fallback_selector: str = "#contentArea .card") -> float:
    """
    Navigate to a page by calling navigate(page_id) in JS.
    Returns elapsed milliseconds from click to DOM ready.
    """
    start = time.perf_counter()

    # Navigate via JS (faster than DOM click)
    await page.evaluate(f"navigate('{page_id}')")

    # Wait for loading overlay lifecyle (appear → disappear)
    try:
        await page.wait_for_selector("#smoothOverlay.active", state="attached", timeout=5000)
        await page.wait_for_selector("#smoothOverlay.active", state="detached", timeout=NAV_TIMEOUT)
    except PlaywrightTimeout:
        pass

    # Wait for primary content indicator
    try:
        await page.wait_for_selector(ready_selector, state="attached", timeout=NAV_TIMEOUT)
    except PlaywrightTimeout:
        try:
            await page.wait_for_selector(fallback_selector, state="attached", timeout=5000)
        except PlaywrightTimeout:
            pass

    # Small render buffer
    await page.wait_for_timeout(200)

    end = time.perf_counter()
    return (end - start) * 1000


# ===== MAIN BENCHMARK =====

async def run_warm_cache_benchmark():
    """
    Protocol for each iteration:
      1. COLD: Navigate to Dashboard (first time after login/login-reload)
      2. WARM-UP: Navigate to Senarai Pengundi (clears Dashboard DOM)
      3. WARM: Navigate back to Dashboard (cache hit expected)
    """
    cold_latencies = []
    warm_latencies = []

    print("=" * 80)
    print("  🏁 JENTERA PINTAR P170 TUARAN — COLD vs WARM CACHE BENCHMARK")
    print(f"  🖥️  Production URL: {BASE_URL}")
    print(f"  👤 User: {USERNAME}  |  Iterations: {ITERATIONS}")
    print(f"  ⏰ Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    print()
    print("  📋 Protocol:")
    print("     ❄️  COLD  = Login → Dashboard (first load, no cache)")
    print(f"     🔄 WARM-UP = Dashboard → Senarai Pengundi (clear Dashboard DOM)")
    print("     🔥 WARM  = Pengundi → Dashboard (cache hit expected)")
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

        for iteration in range(1, ITERATIONS + 1):
            # Create a FRESH context per iteration to avoid localStorage state leak
            context = await browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                locale="ms-MY",
            )
            page = await context.new_page()
            print(f"\n  ─── Iteration {iteration}/{ITERATIONS} ───")

            # --- FRESH LOGIN (cold start) ---
            print(f"  📡 Loading production site...")
            try:
                await page.goto(BASE_URL, wait_until="networkidle", timeout=45000)
                print(f"  ✅ Page loaded")
            except Exception as e:
                print(f"  ❌ Failed to load page: {e}")
                await page.close()
                await context.close()
                continue

            # Authenticate (skip form login on 2nd+ iteration — use direct API login immediately)
            if iteration == 1:
                logged_in = await authenticate(page)
            else:
                logged_in = await do_direct_login(page)
            if not logged_in:
                print(f"  ❌ Login failed. Skipping iteration {iteration}.")
                await page.close()
                await context.close()
                continue

            # --- COLD: Dashboard (first visit after login) ---
            cold_ms = await navigate_and_wait(page, "dashboard")
            cold_latencies.append(cold_ms)
            print(f"  ❄️  COLD Dashboard: {cold_ms:.0f} ms")

            # --- WARM-UP: Navigate to Senarai Pengundi ---
            warmup_ms = await navigate_and_wait(page, WARMUP_PAGE, ready_selector="#contentArea table",
                                                 fallback_selector="#contentArea .table-responsive")
            print(f"  🔄 WARM-UP ({WARMUP_PAGE}): {warmup_ms:.0f} ms")

            # --- WARM: Dashboard (cache hit expected) ---
            warm_ms = await navigate_and_wait(page, "dashboard")
            warm_latencies.append(warm_ms)
            print(f"  🔥 WARM Dashboard: {warm_ms:.0f} ms")

            # --- Delta ---
            delta = cold_ms - warm_ms
            pct = ((cold_ms - warm_ms) / cold_ms) * 100 if cold_ms > 0 else 0
            arrow = "⚡" if delta > 50 else ("📈" if delta > 0 else "🔻")
            print(f"  {arrow} Delta: {delta:+.0f} ms ({pct:+.1f}%)")

            await page.close()

        await browser.close()

    return cold_latencies, warm_latencies


def print_comparison_table(cold: list, warm: list):
    """Print formatted Cold vs Warm comparison table with deltas."""
    print()
    print("=" * 80)
    print("  📊 COLD-START vs WARM-CACHE — SPEED COMPARISON")
    print("=" * 80)
    print(f"  Production: {BASE_URL}")
    print(f"  Timestamp:  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Iterations: {len(cold)} paired cycles")
    print()

    # Individual iteration results
    print(f"  {'Iteration':<12} {'❄️ Cold (ms)':<15} {'🔥 Warm (ms)':<15} {'⚡ Delta (ms)':<15} {'% Faster':<10}")
    print(f"  {'-'*12} {'-'*15} {'-'*15} {'-'*15} {'-'*10}")

    deltas = []
    pcts = []
    for i, (c, w) in enumerate(zip(cold, warm), 1):
        d = c - w
        p = ((c - w) / c) * 100 if c > 0 else 0
        deltas.append(d)
        pcts.append(p)
        arrow = "⚡" if d >= 50 else ("📈" if d > 0 else "🔻")
        print(f"  {i:<12} {c:<15.0f} {w:<15.0f} {d:<+14.0f} {p:<+9.1f}% {arrow}")

    # Summary row
    print(f"  {'-'*12} {'-'*15} {'-'*15} {'-'*15} {'-'*10}")

    avg_cold = sum(cold) / len(cold)
    avg_warm = sum(warm) / len(warm)
    avg_delta = sum(deltas) / len(deltas)
    avg_pct = sum(pcts) / len(pcts)

    min_cold = min(cold)
    max_cold = max(cold)
    min_warm = min(warm)
    max_warm = max(warm)
    min_delta = min(deltas)
    max_delta = max(deltas)

    print(f"  {'AVERAGE':<12} {avg_cold:<15.0f} {avg_warm:<15.0f} {avg_delta:<+14.0f} {avg_pct:<+9.1f}%")
    print(f"  {'MIN':<12} {min_cold:<15.0f} {min_warm:<15.0f} {min_delta:<+14.0f}")
    print(f"  {'MAX':<12} {max_cold:<15.0f} {max_warm:<15.0f} {max_delta:<+14.0f}")

    print()
    verdict = "✅ PASS" if avg_delta >= 50 else "⚠️ MARGINAL" if avg_delta >= 20 else "❌ FAIL"
    target = "<50ms" if avg_delta >= 50 else "not met"
    print(f"  🎯 Target: <50ms improvement → {verdict} (avg delta: {avg_delta:.0f}ms, target {target})")
    print()
    print("  LEGEND:")
    print("    ⚡ Significant improvement (≥50ms)")
    print("    📈 Minor improvement")
    print("    🔻 Regression (Warm slower than Cold)")
    print()
    print("=" * 80)

    return {
        "cold": {
            "avg_ms": round(avg_cold, 1),
            "min_ms": round(min_cold, 1),
            "max_ms": round(max_cold, 1),
            "latencies_ms": [round(l, 1) for l in cold],
        },
        "warm": {
            "avg_ms": round(avg_warm, 1),
            "min_ms": round(min_warm, 1),
            "max_ms": round(max_warm, 1),
            "latencies_ms": [round(l, 1) for l in warm],
        },
        "delta": {
            "avg_ms": round(avg_delta, 1),
            "min_ms": round(min_delta, 1),
            "max_ms": round(max_delta, 1),
            "pct": round(avg_pct, 1),
        },
        "verdict": verdict,
        "target_met": avg_delta >= 50,
    }


async def main():
    print("=" * 80)
    print("  🚀 JENTERA PINTAR P170 TUARAN — WARM-CACHE BENCHMARK")
    print(f"  📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    print()

    cold_latencies, warm_latencies = await run_warm_cache_benchmark()

    if not cold_latencies or not warm_latencies:
        print("❌ Benchmark gagal — tiada keputusan.")
        sys.exit(1)

    summary = print_comparison_table(cold_latencies, warm_latencies)

    # Save JSON results
    output_json = "benchmark_warm_cache_results.json"
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "production_url": BASE_URL,
            "iterations": ITERATIONS,
            "protocol": "COLD: Login→Dashboard, WARM-UP: Dashboard→Pengundi, WARM: Pengundi→Dashboard",
            **summary,
        }, f, indent=2, ensure_ascii=False)
    print(f"\n📁 Results saved to: {output_json}")

    # Save readable text
    output_txt = "benchmark_warm_cache_results.txt"
    with open(output_txt, "w", encoding="utf-8") as f:
        f.write("COLD-START vs WARM-CACHE BENCHMARK\n")
        f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Production: {BASE_URL}\n")
        f.write(f"Iterations: {len(cold_latencies)}\n\n")
        f.write(f"{'Iteration':<12} {'Cold (ms)':<15} {'Warm (ms)':<15} {'Delta (ms)':<15} {'% Faster':<10}\n")
        f.write(f"{'-'*12} {'-'*15} {'-'*15} {'-'*15} {'-'*10}\n")
        for i, (c, w) in enumerate(zip(cold_latencies, warm_latencies), 1):
            d = c - w
            p = ((c - w) / c) * 100 if c > 0 else 0
            f.write(f"{i:<12} {c:<15.0f} {w:<15.0f} {d:<+14.0f} {p:<+9.1f}%\n")
        f.write(f"{'-'*12} {'-'*15} {'-'*15} {'-'*15} {'-'*10}\n")
        avg_cold = sum(cold_latencies) / len(cold_latencies)
        avg_warm = sum(warm_latencies) / len(warm_latencies)
        avg_delta = avg_cold - avg_warm
        f.write(f"{'AVERAGE':<12} {avg_cold:<15.0f} {avg_warm:<15.0f} {avg_delta:<+14.0f}\n")
        f.write(f"\nVerdict: {summary['verdict']} (target <50ms improvement)\n")
    print(f"📁 Readable summary saved to: {output_txt}")


if __name__ == "__main__":
    asyncio.run(main())