"""独立测试脚本：验证 _inject_data_into_html 和 _ensure_html_completeness 的修复效果"""
import json
import re
import os

# 加载缓存数据
cache_file = "report/analysis_data/analysis_data_601006_20260214_205340.json"
with open(cache_file, "r", encoding="utf-8") as f:
    analysis_data = json.load(f)

# 读取截断的HTML文件
truncated_html_file = "report/html/html_601006_20260214_205340.html"
with open(truncated_html_file, "r", encoding="utf-8") as f:
    truncated_html = f.read()

print(f"=== Original truncated file ===")
print(f"Total chars: {len(truncated_html)}")
print(f"Total lines: {len(truncated_html.splitlines())}")
print(f"Has </html>: {'</html>' in truncated_html}")
print(f"Has </body>: {'</body>' in truncated_html}")
print(f"reportData count: {truncated_html.count('reportData =')}")

# ===== Step 1: Brace-counting replacement =====
print(f"\n=== Step 1: Brace-counting data injection ===")

safe_data = json.dumps(analysis_data, ensure_ascii=True, indent=2, separators=(',', ': '), sort_keys=True)
print(f"Injected data length: {len(safe_data)} chars")

html_content = truncated_html

declaration_prefixes = [
    r'\b(?:const|let|var)\s+reportData\s*=\s*',
    r'window\.(?:pageData|reportData)\s*=\s*',
]

injection_success = False
for prefix_idx, prefix_pattern in enumerate(declaration_prefixes):
    match = re.search(prefix_pattern, html_content, re.IGNORECASE)
    if not match:
        continue
    
    brace_start = html_content.find('{', match.end() - 1)
    if brace_start == -1:
        continue
    
    depth = 0
    i = brace_start
    found_end = False
    while i < len(html_content):
        ch = html_content[i]
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                obj_end = i + 1
                if obj_end < len(html_content) and html_content[obj_end] == ';':
                    obj_end += 1
                print(f"Found complete JSON: pos {brace_start}-{i}, len {i - brace_start + 1}")
                html_content = html_content[:brace_start] + safe_data + ';' + html_content[obj_end:]
                print(f"Replaced. New HTML length: {len(html_content)}")
                injection_success = True
                found_end = True
                break
        elif ch == '"':
            i += 1
            while i < len(html_content) and html_content[i] != '"':
                if html_content[i] == '\\':
                    i += 1
                i += 1
        elif ch == "'":
            i += 1
            while i < len(html_content) and html_content[i] != "'":
                if html_content[i] == '\\':
                    i += 1
                i += 1
        i += 1
    
    if found_end:
        break

print(f"Injection success: {injection_success}")
print(f"reportData count after injection: {html_content.count('reportData =')}")

# ===== Step 2: HTML completeness repair =====
print(f"\n=== Step 2: HTML completeness repair ===")

def ensure_html_completeness(html_content):
    html_close_match = re.search(r'</html>', html_content, re.IGNORECASE)
    if html_close_match:
        trailing = html_content[html_close_match.end():].strip()
        if trailing:
            print(f"  Removing {len(trailing)} trailing chars after </html>")
            html_content = html_content[:html_close_match.end()].rstrip() + '\n'
        return html_content
    
    print("  HTML truncated (missing </html>), repairing...")
    
    script_opens = [m.start() for m in re.finditer(r'<script(?:\s[^>]*)?>',  html_content, re.IGNORECASE)]
    script_closes = [m.start() for m in re.finditer(r'</script>', html_content, re.IGNORECASE)]
    
    unclosed_scripts = len(script_opens) - len(script_closes)
    print(f"  Unclosed <script> tags: {unclosed_scripts}")
    
    repair_suffix = ''
    if unclosed_scripts > 0:
        all_report_data = list(re.finditer(r'\b(?:const|let|var)\s+reportData\s*=\s*', html_content, re.IGNORECASE))
        if len(all_report_data) > 1:
            last_decl = all_report_data[-1]
            cut_pos = last_decl.start()
            before_decl = html_content[:cut_pos]
            last_semicolon = before_decl.rfind(';')
            if last_semicolon != -1 and (cut_pos - last_semicolon) < 200:
                cut_pos = last_semicolon + 1
            
            html_content = html_content[:cut_pos].rstrip()
            print(f"  Removed truncated duplicate at {last_decl.start()}, cut at {cut_pos}")
            script_opens_new = len(re.findall(r'<script(?:\s[^>]*)?>',  html_content, re.IGNORECASE))
            script_closes_new = len(re.findall(r'</script>', html_content, re.IGNORECASE))
            unclosed_scripts = script_opens_new - script_closes_new
            print(f"  Recalculated unclosed scripts: {unclosed_scripts}")
        
        if unclosed_scripts > 0:
            repair_suffix += '\n</script>' * unclosed_scripts
    
    has_body_close = bool(re.search(r'</body>', html_content, re.IGNORECASE))
    has_html_close = bool(re.search(r'</html>', html_content + repair_suffix, re.IGNORECASE))
    
    if not has_body_close:
        repair_suffix += '\n</body>'
    if not has_html_close:
        repair_suffix += '\n</html>\n'
    
    if repair_suffix:
        html_content = html_content.rstrip() + repair_suffix
        print(f"  Applied repair suffix: {repr(repair_suffix[:80])}")
    
    return html_content

html_content = ensure_html_completeness(html_content)

# ===== Final validation =====
print(f"\n=== Final Validation ===")
lines = html_content.splitlines()
print(f"Final line count: {len(lines)}")
print(f"Final char count: {len(html_content)}")
print(f"Has </html>: {'</html>' in html_content}")
print(f"Has </body>: {'</body>' in html_content}")
print(f"Has </script>: {'</script>' in html_content}")
print(f"reportData count: {html_content.count('reportData =')}")

# Check that data is actually present
has_battle_data = '"battle_results"' in html_content or "'battle_results'" in html_content
has_research_data = '"research_results"' in html_content or "'research_results'" in html_content
print(f"Has battle_results data: {has_battle_data}")
print(f"Has research_results data: {has_research_data}")

print(f"\nLast 5 lines:")
for line in lines[-5:]:
    print(f"  {line}")

# Save
output_file = "report/html/html_601006_fixed.html"
os.makedirs(os.path.dirname(output_file), exist_ok=True)
with open(output_file, "w", encoding="utf-8") as f:
    f.write(html_content)
print(f"\nFixed file saved to: {output_file}")

all_ok = (
    '</html>' in html_content and
    '</body>' in html_content and
    html_content.count('reportData =') == 1 and
    has_battle_data and
    has_research_data
)

if all_ok:
    print("\n[PASS] Truncation fix successful! HTML is complete with injected data.")
else:
    print("\n[FAIL] Issues remain")
