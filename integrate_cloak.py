"""
Add the photo-cloak research preview to FirstHour (README.md Part 2, steps 2.2-2.6).

Run from the FirstHour repo root:
    python integrate_cloak.py                 # photo-cloak folder at ../photo-cloak
    python integrate_cloak.py --cloak PATH    # photo-cloak folder elsewhere
    python integrate_cloak.py --dry-run       # show what would change, touch nothing

It changes only the four items allowed in Part 2.1:
    extras/photo-cloak/ (new), app/static/cloak_compare.png (new),
    app/templates/portal.html (one card added), README.md (one section added).
If any check fails, it restores everything and exits with an error.
It runs no git commands and never adds file inputs or upload routes.
"""

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

PORTAL = Path("app/templates/portal.html")
README = Path("README.md")
STATIC_IMG = Path("app/static/cloak_compare.png")
EXTRAS = Path("extras/photo-cloak")
BACKUP = Path(".cloak_backup")

COPY_SCRIPTS = ["cloak.py", "transfer_check.py", "README.md", "requirements.txt"]
COPY_RESULTS = ["out/results.txt", "out/transfer.txt", "out/compare.png"]


def fail(msg):
    raise RuntimeError(msg)


# ---------- checks ----------

def pytest_count():
    r = subprocess.run([sys.executable, "-m", "pytest", "-q"], capture_output=True, text=True)
    m = re.search(r"(\d+) passed", r.stdout + r.stderr)
    failed = re.search(r"(\d+) (failed|error)", r.stdout + r.stderr)
    return (int(m.group(1)) if m else 0), (failed.group(0) if failed else None)


def app_check():
    code = (
        "from fastapi.testclient import TestClient\n"
        "from app.main import app\n"
        "c = TestClient(app)\n"
        "p = c.get('/')\n"
        "assert p.status_code == 200 and 'photo cloak' in p.text, 'card missing'\n"
        "i = c.get('/static/cloak_compare.png')\n"
        "assert i.status_code == 200, 'image not served'\n"
        "print('integration OK')\n"
    )
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    return r.returncode == 0 and "integration OK" in r.stdout, (r.stdout + r.stderr).strip()[-400:]


# ---------- portal card ----------

def static_src(html):
    # Reuse exactly how the page already references widget.css.
    m = re.search(r"""(href|src)\s*=\s*(["'])((?:(?!\2).)*widget\.css(?:(?!\2).)*)\2""", html)
    if not m:
        fail("Could not find how portal.html references widget.css, so the static path is unknown.")
    return m.group(3).replace("widget.css", "cloak_compare.png")


def find_support_card(html):
    # The card is the nearest non-heading element with a class, opened before
    # the "Student support" text; find where it closes.
    hit = re.search(r"student\s+support", html, re.I)
    if not hit:
        fail("Could not find the 'Student support' card in portal.html.")
    opens = list(re.finditer(r"<(?!h[1-6]\b)([a-zA-Z][a-zA-Z0-9]*)\b([^>]*\bclass\s*=\s*([\"'])[^\"']*\3[^>]*)>",
                             html[:hit.start()]))
    if not opens:
        fail("Could not find the element that wraps the Student support card.")
    start = opens[-1]
    tag, attrs = start.group(1).lower(), start.group(2)
    cls = re.search(r"\bclass\s*=\s*([\"'])([^\"']*)\1", attrs).group(2)
    depth, pos = 0, start.start()
    for m in re.finditer(rf"<(/?){tag}\b[^>]*>", html[pos:], re.I):
        depth += -1 if m.group(1) else 1
        if depth == 0:
            return tag, cls, pos + m.end(), html[:start.start()].rsplit("\n", 1)[-1]
    fail("Could not find where the Student support card ends.")


def card_html(tag, cls, src, indent):
    i = indent if indent.strip() == "" else ""
    return (
        f"\n{i}<{tag} class=\"{cls}\">\n"
        f"{i}  <h2>Before you post: photo cloak (research preview)</h2>\n"
        f"{i}  <p>We are testing a tool that adds a small change to a photo so face-recognition "
        f"software stops matching it to you. It runs on your own device, so the school never sees your photos.</p>\n"
        f"{i}  <img src=\"{src}\" alt=\"Original photo, cloaked photo, and the change magnified ten times\" "
        f"style=\"width: 100%; height: auto; border-radius: 8px\">\n"
        f"{i}  <p><small>Research preview, not available yet. It does not stop nudify apps.</small></p>\n"
        f"{i}</{tag}>"
    )


# ---------- README section ----------

def parse_results(results, transfer):
    def value(text, label):
        m = re.search(rf"^\s*{re.escape(label)}(?:\s*\(baseline\))?\s+(-?\d+\.\d+)", text, re.M)
        return m.group(1) if m else "not measured"

    labels = ["Original after JPEG 80", "Cloaked", "Cloaked after JPEG 80", "Cloaked after resize and JPEG 80"]
    out = ["| Image | Model tuned against (VGGFace2) | Second model, never seen (CASIA-WebFace) |",
           "|---|---|---|"]
    for label in labels:
        name = label + (" (baseline)" if label.startswith("Original") else "")
        out.append(f"| {name} | {value(results, label)} | {value(transfer, label)} |")
    psnr = re.search(r"PSNR[^:]*:\s*([\d.]+) dB", results)
    if psnr:
        out.append("")
        out.append(f"PSNR original vs cloaked: {psnr.group(1)} dB.")
    return "\n".join(out)


def add_readme_section(text, table):
    m = re.search(r"^(#{1,6})\s*Limits\b.*$", text, re.I | re.M)
    if not m:
        fail("Could not find a 'Limits' section heading in README.md.")
    level = len(m.group(1))
    nxt = re.search(rf"^#{{1,{level}}}\s", text[m.end():], re.M)
    at = m.end() + nxt.start() if nxt else len(text)
    section = (
        f"{'#' * level} Prevention research (separate tool)\n\n"
        "`extras/photo-cloak` cloaks the face in a public-domain photo against a face-recognition "
        "model (FaceNet). It is meant to run on the student's own device and is separate from the app, "
        "which never accepts images.\n\n"
        f"{table}\n\n"
        "Limits: it only partly transfers to a model it never saw, research shows cloaks can be stripped "
        "(Honig, Rando, Carlini, Tramer, 2024), and it does not protect against nudify or face-swap apps.\n\n"
        "How to run: see extras/photo-cloak/README.md.\n\n"
    )
    before = text[:at].rstrip("\n") + "\n\n"
    return before + section + text[at:].lstrip("\n")


# ---------- backup / rollback ----------

def backup():
    BACKUP.mkdir(exist_ok=True)
    shutil.copy2(PORTAL, BACKUP / "portal.html")
    shutil.copy2(README, BACKUP / "README.md")


def rollback():
    shutil.copy2(BACKUP / "portal.html", PORTAL)
    shutil.copy2(BACKUP / "README.md", README)
    if STATIC_IMG.exists():
        STATIC_IMG.unlink()
    if EXTRAS.exists():
        shutil.rmtree(EXTRAS)
    if EXTRAS.parent.exists() and not any(EXTRAS.parent.iterdir()):
        EXTRAS.parent.rmdir()
    print("Rolled back: portal.html and README.md restored, added files removed.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cloak", default="../photo-cloak", help="path to the photo-cloak folder")
    ap.add_argument("--dry-run", action="store_true", help="print the changes, write nothing")
    ap.add_argument("--skip-tests", action="store_true", help="skip pytest and the app check")
    args = ap.parse_args()
    cloak = Path(args.cloak)

    # Preconditions
    for p in (PORTAL, README):
        if not p.exists():
            sys.exit(f"Run this from the FirstHour repo root: {p} not found.")
    missing = [f for f in COPY_SCRIPTS + COPY_RESULTS if not (cloak / f).exists()]
    if missing:
        sys.exit(f"Missing in {cloak}: {', '.join(missing)}. Run Part 1 (cloak.py and transfer_check.py) first.")
    if EXTRAS.exists() or STATIC_IMG.exists() or "photo cloak (research preview)" in PORTAL.read_text(encoding="utf-8"):
        sys.exit("Looks already integrated (extras/photo-cloak, the image, or the card exists). Nothing changed.")

    portal = PORTAL.read_text(encoding="utf-8")
    readme = README.read_text(encoding="utf-8")
    try:
        src = static_src(portal)
        tag, cls, end, indent = find_support_card(portal)
        new_portal = portal[:end] + card_html(tag, cls, src, indent) + portal[end:]
        table = parse_results((cloak / "out/results.txt").read_text(encoding="utf-8"),
                              (cloak / "out/transfer.txt").read_text(encoding="utf-8"))
        new_readme = add_readme_section(readme, table)
    except RuntimeError as e:
        sys.exit(f"Stopped before changing anything: {e}")

    if args.dry_run:
        print("--- card to add after the Student support card ---")
        print(card_html(tag, cls, src, indent))
        print("\n--- README section to add after Limits ---")
        print(new_readme[len(readme[:readme.lower().find("limits")]):][:1500])
        return

    before = None
    if not args.skip_tests:
        before, bad = pytest_count()
        print(f"pytest before: {before} passed" + (f" ({bad})" if bad else ""))

    backup()
    try:
        EXTRAS.mkdir(parents=True)
        for f in COPY_SCRIPTS + COPY_RESULTS:
            shutil.copy2(cloak / f, EXTRAS / Path(f).name)
        STATIC_IMG.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(cloak / "out/compare.png", STATIC_IMG)
        PORTAL.write_text(new_portal, encoding="utf-8")
        README.write_text(new_readme, encoding="utf-8")

        if 'type="file"' in new_portal or "type='file'" in new_portal:
            fail("portal.html contains a file input")
        if not args.skip_tests:
            after, bad = pytest_count()
            if after != before or bad:
                fail(f"pytest changed: {before} passed before, {after} after" + (f" ({bad})" if bad else ""))
            ok, log = app_check()
            if not ok:
                fail(f"app check failed: {log}")
    except Exception as e:
        print(f"Check failed: {e}")
        rollback()
        sys.exit(1)

    n = len(list(EXTRAS.iterdir()))
    print("Files changed: portal.html (card added), README.md (section added)")
    print(f"Files added: extras/photo-cloak/ ({n} files), app/static/cloak_compare.png")
    print(f"pytest: {before} passed (same as before: yes)" if before is not None else "pytest: skipped")
    print("File inputs in portal: 0")
    print("Card check: integration OK" if not args.skip_tests else "Card check: skipped")
    print(f"Backups kept in {BACKUP}/ (delete when happy).")


if __name__ == "__main__":
    main()
