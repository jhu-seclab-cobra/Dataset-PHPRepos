#!/usr/bin/env python3
"""Extract PHPRepos source archives into repos/<owner>_<repo>/codes/.

Examples:
    python tools/extract.py                                 # every repository
    python tools/extract.py --top 50                        # the 50 highest ranked
    python tools/extract.py pterodactyl_panel humhub_humhub # named repositories

Each archive is checked against the sha256 values in its meta.json. A repository
whose codes/ directory already exists is skipped unless --force is given.
Requires Python 3.12 or later and no third-party packages.
"""
import argparse
import hashlib
import json
import shutil
import sys
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class Parts:
    """Read the archive parts as one stream and hash the bytes read."""

    def __init__(self, repo_dir, parts):
        self.files = [(repo_dir / p["path"], p["sha256"]) for p in parts]
        self.total = hashlib.sha256()
        self.part = None
        self.fh = None
        self.expected = None

    def _next(self):
        if self.fh:
            self._close_part()
        if not self.files:
            return False
        path, self.expected = self.files.pop(0)
        self.fh = open(path, "rb")
        self.part = hashlib.sha256()
        return True

    def _close_part(self):
        self.fh.close()
        self.fh = None
        if self.part.hexdigest() != self.expected:
            raise ValueError("sha256 mismatch in an archive part")

    def read(self, n=-1):
        if self.fh is None and not self._next():
            return b""
        while True:
            b = self.fh.read(n)
            if b:
                self.part.update(b)
                self.total.update(b)
                return b
            if not self._next():
                return b""

    def drain(self):
        while self.read(1 << 20):
            pass


def extract(repo_dir, force):
    meta = json.loads((repo_dir / "meta.json").read_text())
    pkg = meta["source_package"]
    dest = repo_dir / "codes"
    if dest.exists() and not force:
        return "skipped"
    tmp = repo_dir / "codes.partial"
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir()
    stream = Parts(repo_dir, pkg["parts"])
    try:
        with tarfile.open(fileobj=stream, mode="r|xz") as tar:
            tar.extractall(tmp, filter="tar")
        stream.drain()
        if stream.total.hexdigest() != pkg["archive_sha256"]:
            raise ValueError("archive sha256 mismatch")
    except Exception:
        shutil.rmtree(tmp, ignore_errors=True)
        raise
    shutil.rmtree(dest, ignore_errors=True)
    tmp.rename(dest)
    return "extracted"


def rank(repo_dir):
    return json.loads((repo_dir / "meta.json").read_text())["rank"]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("repos", nargs="*", help="datapoint names, e.g. pterodactyl_panel (default: all)")
    ap.add_argument("--top", type=int, help="only the N highest ranked repositories")
    ap.add_argument("--force", action="store_true", help="re-extract repositories whose codes/ exists")
    args = ap.parse_args()

    dirs = sorted(p.parent for p in (ROOT / "repos").glob("*/meta.json"))
    if args.repos:
        names = set(args.repos)
        missing = names - {d.name for d in dirs}
        if missing:
            sys.exit(f"unknown repository: {', '.join(sorted(missing))}")
        dirs = [d for d in dirs if d.name in names]
    if args.top is not None:
        dirs = sorted(sorted(dirs, key=rank)[:args.top])

    failed = 0
    for i, d in enumerate(dirs, 1):
        try:
            status = extract(d, args.force)
        except Exception as e:
            status, failed = f"FAILED: {e}", failed + 1
        print(f"[{i}/{len(dirs)}] {d.name} {status}", flush=True)
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
