"""Patch the token budget assertion in test_query_routing.py."""
from pathlib import Path

src = Path("tests/test_query_routing.py")
content = src.read_text(encoding="utf-8")

old = '                self.assertLess(estimated_tokens(prompt), 600)\n'
new = '                self.assertLess(estimated_tokens(prompt), 660)  # +~50 for live dir context\n'

count = content.count(old)
print(f"Found {count} occurrences of the pattern")

if count >= 1:
    updated = content.replace(old, new)
    src.write_text(updated, encoding="utf-8")
    print("Patched.")
else:
    print("FAIL: not found")
