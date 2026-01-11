# dump_project_to_txt.py
"""
Erzeugt eine einzelne project_dump.txt mit:
- Ordnerbaum
- Inhalt aller Textdateien (py, html, css, js, json, md, txt, ini, cfg, env*)
- schließt große/binäre Dateien aus (media, venv, __pycache__, .git, node_modules, *.pyc, *.sqlite*)
Nutzung:
    python dump_project_to_txt.py /pfad/zum/projekt
Die Ausgabe landet neben dem Skript als project_dump.txt
"""
import sys, os, mimetypes

ROOT = sys.argv[1] if len(sys.argv) > 1 else "."
OUT = "project_dump.txt"

EXCLUDE_DIRS = {
    ".git", "__pycache__", "venv", "env",
    "node_modules", "media", "staticfiles",
    "a1_OLD"  # <-- hier ergänzt
}
EXCLUDE_GLOBS = (".pyc", ".pyo", ".sqlite", ".sqlite3", ".db", ".log", ".lock")
TEXT_EXTS = {
    ".py", ".html", ".htm", ".css", ".js", ".json",
    ".md", ".txt", ".ini", ".cfg", ".yaml", ".yml",
    ".env", ".toml"
}
MAX_FILE_MB = 2

def is_text_file(path):
    ext = os.path.splitext(path)[1].lower()
    if ext in TEXT_EXTS:
        return True
    kind, _ = mimetypes.guess_type(path)
    return kind and kind.startswith("text")

def should_skip_file(path):
    name = os.path.basename(path)
    if any(name.endswith(g) for g in EXCLUDE_GLOBS):
        return True
    if os.path.getsize(path) > MAX_FILE_MB * 1024 * 1024:
        return True
    return False

with open(OUT, "w", encoding="utf-8", errors="ignore") as out:
    out.write(f"# PROJECT DUMP FROM: {os.path.abspath(ROOT)}\n\n")
    out.write("## TREE\n")
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
        rel = os.path.relpath(dirpath, ROOT)
        depth = 0 if rel == "." else rel.count(os.sep) + 1
        out.write("  " * depth + f"- {os.path.basename(dirpath) if rel!='.' else os.path.basename(os.path.abspath(ROOT))}\n")
        for f in sorted(filenames):
            if should_skip_file(os.path.join(dirpath, f)):
                continue
            out.write("  " * (depth + 1) + f"- {f}\n")

    out.write("\n\n## FILE CONTENTS\n")
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
        for f in sorted(filenames):
            fp = os.path.join(dirpath, f)
            if should_skip_file(fp):
                continue
            if not is_text_file(fp):
                continue
            rel = os.path.relpath(fp, ROOT)
            out.write("\n" + "="*80 + f"\n# FILE: {rel}\n" + "="*80 + "\n")
            try:
                with open(fp, "r", encoding="utf-8", errors="ignore") as fh:
                    out.write(fh.read())
            except Exception as e:
                out.write(f"\n[SKIPPED: {e}]\n")

print(f"✅ Fertig: {OUT}")
