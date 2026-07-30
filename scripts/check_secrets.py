#!/usr/bin/env python3
import re, subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
FORBIDDEN = [re.compile(r"(^|/)\.env$"), re.compile(r"\.(pem|key|p12)$"), re.compile(r"\.db$"), re.compile(r"uploads/")]
SECRETS = [("API key", re.compile(r"sk-(?:ant-)?[A-Za-z0-9_\-]{20,}")), ("Private key", re.compile(r"-----BEGIN .* PRIVATE KEY-----"))]
ALLOW = re.compile(r"(?i)(example|placeholder|changeme|xxx|dummy|redacted|sk-ant-\.\.\.\.|check_secrets\.py|re\.compile)")
SKIP = {".png",".jpg",".pdf",".zip",".gz",".db",".ico"}
def files():
    try:
        out = subprocess.run(["git","ls-files","--cached","--others","--exclude-standard"], cwd=ROOT, capture_output=True, text=True, check=False)
        if out.returncode == 0: return out.stdout.splitlines()
    except FileNotFoundError: pass
    return [str(p.relative_to(ROOT)) for p in ROOT.rglob("*") if p.is_file() and ".git/" not in str(p)]
def main():
    fs = files(); findings = []
    for f in fs:
        for pat in FORBIDDEN:
            if pat.search(f): findings.append(f"FORBIDDEN: {f}"); break
    for f in fs:
        p = ROOT / f
        if not p.is_file() or p.suffix.lower() in SKIP: continue
        try:
            if p.stat().st_size > 2_000_000: continue
            text = p.read_text(errors="ignore")
        except OSError: continue
        for lineno, line in enumerate(text.splitlines(), 1):
            if ALLOW.search(line): continue
            for label, pat in SECRETS:
                if pat.search(line): findings.append(f"SECRET ({label}) at {f}:{lineno}")
    print(f"Scanned {len(fs)} file(s).")
    if findings:
        for f in findings: print(f"  {f}")
        return 1
    print("PASS"); return 0
if __name__ == "__main__": sys.exit(main())
