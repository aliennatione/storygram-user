#!/usr/bin/env python3
"""Helper for the demo-authoring skill: probe, install, scaffold, render.

Usage:
  PYTHONPATH=/data/src python /data/scripts/demo_tools.py status
  ... scaffold manim <name>
  ... scaffold vcr <module>
  ... render manim <file.py> [--quality low|medium|high]
  ... install manim --yes
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path("/data")
SKILL = ROOT / ".opencode" / "skills" / "demo-authoring"
TEMPLATES = SKILL / "templates"
OUT_ROOT = ROOT / "generated" / "demos"


def which(cmd: str) -> str | None:
    return shutil.which(cmd)


def version(cmd: str, args: list[str]) -> str | None:
    exe = which(cmd)
    if not exe:
        return None
    try:
        r = subprocess.run([exe, *args], capture_output=True, text=True, timeout=30)
        out = (r.stdout or r.stderr).strip().splitlines()
        return out[0] if out else None
    except Exception as e:  # pragma: no cover
        return f"error: {e}"


def status() -> dict:
    return {
        "manim": {
            "available": which("manim") is not None,
            "version": version("manim", ["--version"]),
            "install_hint": (
                "apk add ffmpeg cairo pango pango-dev texlive fontconfig "
                "ttf-dejavu build-base python3-dev && "
                "pip install --break-system-packages manim"
            ),
        },
        "vcr": {
            "available": which("vcr") is not None,
            "version": version("vcr", ["version"]) or version("vcr", ["--version"]),
            "install_hint": (
                "Ubuntu host with snapd: sudo snap install video-course-recorder --edge "
                "&& sudo snap alias video-course-recorder vcr"
            ),
        },
        "slidev": {
            "available": which("slidev") is not None,
            "version": version("slidev", ["--version"]),
            "install_hint": "npm install -g @slidev/cli @slidev/theme-default",
        },
        "ffmpeg": {
            "available": which("ffmpeg") is not None,
            "version": version("ffmpeg", ["-version"]),
        },
        "texlive": {"available": which("pdflatex") is not None or which("xelatex") is not None},
        "python": sys.version,
    }


def cmd_status(_args) -> int:
    print(json.dumps(status(), indent=2, ensure_ascii=False))
    return 0


def cmd_install(args) -> int:
    if args.tool != "manim":
        print(f"install non supportato per: {args.tool}", file=sys.stderr)
        return 2
    if not args.yes:
        print("Riesegui con --yes per installare Manim (pesante).", file=sys.stderr)
        return 1
    cmds = [
        [
            "apk",
            "add",
            "--no-cache",
            "ffmpeg",
            "cairo",
            "pango",
            "pango-dev",
            "texlive",
            "fontconfig",
            "ttf-dejavu",
            "build-base",
            "python3-dev",
        ],
        [sys.executable, "-m", "pip", "install", "--break-system-packages", "manim"],
    ]
    for c in cmds:
        print("+", " ".join(c))
        r = subprocess.run(c)
        if r.returncode != 0:
            return r.returncode
    print("Manim installato. Verifica:", version("manim", ["--version"]))
    return 0


def cmd_scaffold(args) -> int:
    if args.kind == "manim":
        name = args.name
        dest_dir = OUT_ROOT / "manim"
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / f"{name}.py"
        src = TEMPLATES / "manim_scene.py"
        dest.write_text(src.read_text())
        print(f"Creato: {dest}")
        return 0
    if args.kind == "vcr":
        module = args.name
        base = OUT_ROOT / "vcr" / module
        (base / "en").mkdir(parents=True, exist_ok=True)
        tmpl = (TEMPLATES / "vcr_module.md").read_text().replace("Modulo demo", module)
        (base / "en" / "index.md").write_text(tmpl)
        pkg = (TEMPLATES / "vcr_package.json").read_text().replace("vcr-demo-module", module)
        (base / "package.json").write_text(pkg)
        print(f"Creato content repo: {base}")
        return 0
    print(f"kind sconosciuto: {args.kind}", file=sys.stderr)
    return 2


def cmd_render(args) -> int:
    if args.kind != "manim":
        print(f"render non supportato per: {args.kind}", file=sys.stderr)
        return 2
    f = Path(args.file).resolve()
    if not f.exists():
        print(f"file non trovato: {f}", file=sys.stderr)
        return 1
    qmap = {"low": "-ql", "medium": "-qm", "high": "-qh"}
    qflag = qmap.get(args.quality, "-ql")
    cmd = ["manim", qflag, str(f), "DemoScene"]
    # detect class name from file
    import re

    text = f.read_text()
    m = re.search(r"class\s+(\w+)\s*\(\s*Scene\s*\)", text)
    if m:
        cmd[-1] = m.group(1)
    print("+", " ".join(cmd))
    r = subprocess.run(cmd, cwd=str(f.parent))
    return r.returncode


def main() -> int:
    p = argparse.ArgumentParser(prog="demo_tools.py")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("status")
    s.set_defaults(func=cmd_status)

    ins = sub.add_parser("install")
    ins.add_argument("tool")
    ins.add_argument("--yes", action="store_true")
    ins.set_defaults(func=cmd_install)

    sc = sub.add_parser("scaffold")
    sc.add_argument("kind")
    sc.add_argument("name")
    sc.set_defaults(func=cmd_scaffold)

    rd = sub.add_parser("render")
    rd.add_argument("kind")
    rd.add_argument("file")
    rd.add_argument("--quality", default="low", choices=["low", "medium", "high"])
    rd.set_defaults(func=cmd_render)

    args = p.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
