"""
Pinpoint exact line of parenthesis/curly-brace imbalance in renderDashboard
"""
content = open('frontend/index.html', 'r', encoding='utf-8').readlines()
start, end = 1158, 1455

print(f"Scanning renderDashboard (L{start}-L{end})")
print("=" * 60)

paren = 0
curly = 0

for i in range(start, end + 1):
    line = content[i - 1]
    old_paren, old_curly = paren, curly
    
    for ch in line:
        if ch == '(': paren += 1
        elif ch == ')': paren -= 1
        elif ch == '{': curly += 1
        elif ch == '}': curly -= 1
    
    if paren != old_paren or curly != old_curly:
        if paren > old_paren or curly > old_curly:
            dir = 'OPEN'
        else:
            dir = 'CLOSE'
        p_str = f"({paren:+3d})"
        c_str = f"({curly:+3d})"
        print(f"L{i:4d} [{p_str} {c_str}] {dir} | {line.strip()[:90]}")

print(f"\nFinal: paren={paren}, curly={curly}")

# Now check specifically the fetchRingkasanData + catch block at L1421-L1454
print("\n" + "=" * 60)
print("FOCUS: L1419-L1455")
print("=" * 60)
for i in range(1419, 1456):
    line = content[i - 1]
    print(f"L{i:4d}: {line.rstrip()}")