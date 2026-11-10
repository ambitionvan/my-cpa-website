#!/usr/bin/env python3
"""
One-click rename for my-cpa-website.

What it does (one command, no manual file edits):
      python3 apply-brand.py --brand "New Firm Name"
      python3 apply-brand.py --brand "New Firm Name" --person "New Name" --domain "https://newdomain.ca"
  It reads the CURRENT names from site-config.json, replaces them
  with the new values in every .html / .xml / .txt / .json file
  under this folder (except .git/ and this script itself), then
  updates site-config.json so the next rename starts from the
  new values. Do NOT edit site-config.json by hand first -- the
  script needs the old values in there to find what to replace.

To change back, run it again with the old values. Same one command.

Dry run (preview only, changes nothing):
      python3 apply-brand.py --dry-run

Usage with arguments (overrides config file):
      python3 apply-brand.py --brand "New Firm Name" --person "New Name"
      python3 apply-brand.py --domain "https://newdomain.ca"

Notes (honest limits):
  - This changes the FILES in one click. Google / Bing / AI search
    take weeks to re-learn a new name or domain; that part cannot
    be one-click.
  - Changing the domain also needs: DNS + GitHub Pages custom-domain
    setting + Google Search Console change of address + keeping the
    old URL redirecting. The script updates the URLs in the files,
    it cannot do DNS for you.
  - Changing the Google Business Profile name is separate: edit it
    in Google Business Profile, it may ask for re-verification.
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONFIG = ROOT / "site-config.json"
SKIP_DIRS = {".git", "__pycache__"}
SKIP_FILES = {"apply-brand.py"}
EXTS = {".html", ".xml", ".txt", ".json", ".md"}


def load_config():
    with open(CONFIG, encoding="utf-8") as f:
        return json.load(f)


def build_replacements(old, new):
    """Longest first, so 'Joseph Zhu, CPA, CGA' is replaced before 'Joseph Zhu'."""
    pairs = []
    keys = [
        ("person_full", "person_full"),
        ("person_legal", "person_legal"),
        ("brand_name", "brand_name"),
        ("brand_alternate", "brand_alternate"),
        ("person_name", "person_name"),
        ("site_url_with_slash", "site_url_with_slash"),
        ("site_url", "site_url"),
    ]
    for old_key, new_key in keys:
        o = (old.get(old_key) or "").strip()
        n = (new.get(new_key) or "").strip()
        if o and n and o != n:
            pairs.append((o, n))
    # Also handle the bare domain host without scheme, derived from site_url.
    for label in ("site_url", "site_url_with_slash"):
        o = (old.get(label) or "").strip().removeprefix("https://").rstrip("/")
        n = (new.get(label) or "").strip().removeprefix("https://").rstrip("/")
        if o and n and o != n and (o, n) not in pairs:
            pairs.append((o, n))
    pairs.sort(key=lambda p: len(p[0]), reverse=True)
    return pairs


def main():
    ap = argparse.ArgumentParser(description="One-click rename for my-cpa-website")
    ap.add_argument("--dry-run", action="store_true", help="preview only, change nothing")
    ap.add_argument("--brand", help="new brand/company name")
    ap.add_argument("--brand-alternate", dest="brand_alternate", help="new alternate name, e.g. the Google listing name")
    ap.add_argument("--person", help="new person name, e.g. 'Joseph Zhu'")
    ap.add_argument("--person-full", dest="person_full", help="new person display, e.g. 'Joseph Zhu, CPA, CGA'")
    ap.add_argument("--person-legal", dest="person_legal", help="new legal name, e.g. 'Zhixiong (Joseph) Zhu'")
    ap.add_argument("--domain", "--site-url", dest="site_url", help="new site URL, e.g. https://greenbeanscpa.ca")
    args = ap.parse_args()

    old = load_config()
    new = dict(old)
    if args.brand:
        new["brand_name"] = args.brand
    if getattr(args, "brand_alternate", None):
        new["brand_alternate"] = args.brand_alternate
    if args.person:
        new["person_name"] = args.person
    if args.person_full:
        new["person_full"] = args.person_full
    if args.person_legal:
        new["person_legal"] = args.person_legal
    if args.site_url:
        new["site_url"] = args.site_url.rstrip("/")
        new["site_url_with_slash"] = args.site_url.rstrip("/") + "/"

    if args.brand and old.get("brand_name") == old.get("person_full"):
        print("Note: the firm name and the person name are currently the same")
        print("text ('Joseph Zhu, CPA, CGA'), so --brand replaces every")
        print("occurrence, including person mentions. If only the firm name")
        print("changes later but you stay Joseph Zhu, tell Muse so the")
        print("firm slots (title / header / schema name / footer) are")
        print("changed separately from the person mentions.")
        print()

    pairs = build_replacements(old, new)
    if not pairs:
        print("No change: pass a new value, e.g.:")
        print('  python3 apply-brand.py --brand "New Firm Name"')
        print('  python3 apply-brand.py --brand "New Firm Name" --domain "https://newdomain.ca"')
        return 0

    print("Replacements (old -> new):")
    for o, n in pairs:
        print(f"  {o!r} -> {n!r}")

    files = [p for p in ROOT.rglob("*") if p.is_file() and p.suffix.lower() in EXTS
             and p.name not in SKIP_FILES and not any(part in SKIP_DIRS for part in p.parts)]
    total = 0
    changed_files = []
    for path in sorted(files):
        text = path.read_text(encoding="utf-8")
        orig = text
        for o, n in pairs:
            text = text.replace(o, n)
        if text != orig:
            count = sum(orig.count(o) for o, _ in pairs)
            # count precisely per file by diffing occurrences is noisy after
            # overlapping replaces; report files changed instead.
            changed_files.append(str(path.relative_to(ROOT)))
            total += 1
            if not args.dry_run:
                path.write_text(text, encoding="utf-8")

    print(f"\nFiles that would change: {len(changed_files)}")
    for f in changed_files:
        print(f"  - {f}")
    if args.dry_run:
        print("\nDry run only, nothing was changed.")
        return 0

    with open(CONFIG, "w", encoding="utf-8") as f:
        json.dump(new, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print("\nDone. site-config.json updated to the new values.")
    print("Next: check with `git diff --stat`, then commit + push. Also update")
    print("the Google Business Profile name to match, if the brand changed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
