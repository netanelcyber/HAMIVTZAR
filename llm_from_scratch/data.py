"""
Data pipeline: collect all available Linux documentation and prepare batches.

Sources (in order of richness):
  1. All man pages — read directly from /usr/share/man/**/*.gz
  2. /usr/share/doc/ — README*, *.md, *.txt, changelog.Debian
  3. /usr/share/info/ — GNU info pages (gunzipped)
  4. /etc/ config files with inline comments
  5. Built-in fallback corpus if everything else fails

Note: Reddit is unavailable in this environment (proxy policy blocks it).
"""

import gzip
import re
import subprocess
import random
import os
from pathlib import Path

import numpy as np


# ---------------------------------------------------------------------------
# Source 1: Man pages  (/usr/share/man/**/*.gz)
# ---------------------------------------------------------------------------

MAN_DIRS = [
    "/usr/share/man/man1",
    "/usr/share/man/man2",
    "/usr/share/man/man3",
    "/usr/share/man/man5",
    "/usr/share/man/man7",
    "/usr/share/man/man8",
]

# Sections we care about most (skip man3 API refs which are very noisy)
PRIORITY_SECTIONS = {"man1", "man5", "man7", "man8"}


def _gunzip_text(path: Path) -> str:
    """Decompress a .gz file and return its text content."""
    try:
        with gzip.open(path, "rt", encoding="utf-8", errors="replace") as f:
            return f.read()
    except Exception:
        return ""


def _strip_troff(text: str) -> str:
    """Very light troff/groff stripping — remove .XX directives and backslash escapes."""
    lines = []
    for line in text.splitlines():
        line = line.strip()
        # Skip pure troff directives
        if line.startswith(".") and len(line) > 1 and not line[1].isdigit():
            continue
        # Remove backslash escapes: \fB, \fI, \fR, \(em, \\, etc.
        line = re.sub(r"\\[fF][BIRPC0-9]", "", line)
        line = re.sub(r"\\[()][a-zA-Z0-9]{2}", " ", line)
        line = re.sub(r"\\.", "", line)
        if line:
            lines.append(line)
    return "\n".join(lines)


def collect_man_pages(max_per_section: int = 200, verbose: bool = False) -> str:
    """Read all man pages from /usr/share/man/. Returns plain text."""
    chunks: list[str] = []
    total = 0
    for section_dir in MAN_DIRS:
        p = Path(section_dir)
        if not p.exists():
            continue
        section = p.name
        count = 0
        for gz_file in sorted(p.glob("*.gz")):
            if count >= max_per_section:
                break
            raw = _gunzip_text(gz_file)
            if not raw.strip():
                continue
            text = _strip_troff(raw)
            if len(text) > 100:
                chunks.append(text)
                count += 1
                total += 1
        if verbose:
            print(f"    {section}: {count} pages")

    if verbose:
        print(f"  man pages total: {total}")
    return "\n\n".join(chunks)


# ---------------------------------------------------------------------------
# Source 2: /usr/share/doc/  (README, changelogs, plain text)
# ---------------------------------------------------------------------------

DOC_PATTERNS = [
    "README*", "readme*",
    "*.md", "*.txt", "*.rst",
    "changelog.Debian", "changelog",
    "NEWS", "TODO", "HACKING", "CONTRIBUTING",
    "copyright",
]

MAX_DOC_FILE_SIZE = 50_000   # bytes — skip huge changelogs


def collect_doc_files(max_files: int = 2000, verbose: bool = False) -> str:
    """Walk /usr/share/doc/ and collect readable text files."""
    doc_root = Path("/usr/share/doc")
    if not doc_root.exists():
        return ""

    chunks: list[str] = []
    seen: set[str] = set()
    count = 0

    for pkg_dir in sorted(doc_root.iterdir()):
        if count >= max_files:
            break
        if not pkg_dir.is_dir():
            continue
        for pattern in DOC_PATTERNS:
            for f in pkg_dir.glob(pattern):
                if count >= max_files:
                    break
                key = str(f)
                if key in seen:
                    continue
                seen.add(key)
                try:
                    size = f.stat().st_size
                    if size > MAX_DOC_FILE_SIZE or size < 50:
                        continue
                    # Try plain read first, then gzip
                    if f.suffix == ".gz":
                        text = _gunzip_text(f)
                    else:
                        text = f.read_text(encoding="utf-8", errors="replace")
                    text = text.strip()
                    if len(text) > 80:
                        chunks.append(text)
                        count += 1
                except Exception:
                    pass

    if verbose:
        print(f"  doc files: {count}")
    return "\n\n".join(chunks)


# ---------------------------------------------------------------------------
# Source 3: /usr/share/info/  (GNU info pages, gzipped)
# ---------------------------------------------------------------------------

def collect_info_pages(max_files: int = 50, verbose: bool = False) -> str:
    """Read GNU info pages from /usr/share/info/."""
    info_dir = Path("/usr/share/info")
    if not info_dir.exists():
        return ""

    chunks: list[str] = []
    count = 0
    for gz_file in sorted(info_dir.glob("*.gz")):
        if count >= max_files:
            break
        text = _gunzip_text(gz_file)
        # Strip info-format control chars
        text = re.sub(r"\x1f[^\n]*\n", "\n", text)   # form-feed markers
        text = re.sub(r"\*[Mm]enu:.*", "", text, flags=re.DOTALL)  # menu sections
        text = text.strip()
        if len(text) > 100:
            chunks.append(text)
            count += 1

    if verbose:
        print(f"  info pages: {count}")
    return "\n\n".join(chunks)


# ---------------------------------------------------------------------------
# Source 4: /etc/ config files (human-readable comments and docs)
# ---------------------------------------------------------------------------

ETC_FILES = [
    "/etc/bash.bashrc", "/etc/profile", "/etc/environment",
    "/etc/fstab", "/etc/hosts", "/etc/hostname", "/etc/resolv.conf",
    "/etc/ssh/sshd_config", "/etc/sudoers",
    "/etc/apt/sources.list",
    "/etc/systemd/system.conf", "/etc/systemd/journald.conf",
    "/etc/security/limits.conf", "/etc/security/access.conf",
    "/etc/sysctl.conf",
    "/etc/crontab",
    "/etc/nftables.conf",
    "/etc/logrotate.conf",
    "/etc/rsyslog.conf",
]


def collect_etc_files(verbose: bool = False) -> str:
    chunks: list[str] = []
    for path_str in ETC_FILES:
        p = Path(path_str)
        try:
            if p.exists():
                text = p.read_text(encoding="utf-8", errors="replace").strip()
                if len(text) > 30:
                    chunks.append(f"# {path_str}\n{text}")
        except Exception:
            pass
    if verbose:
        print(f"  /etc files: {len(chunks)}")
    return "\n\n".join(chunks)


# ---------------------------------------------------------------------------
# Fallback corpus
# ---------------------------------------------------------------------------

FALLBACK_CORPUS = """\
NAME
       ls - list directory contents

SYNOPSIS
       ls [OPTION]... [FILE]...

DESCRIPTION
       List information about the FILEs (the current directory by default).
       Sort entries alphabetically if none of -cftuvSUX nor --sort is specified.

       -a, --all
              do not ignore entries starting with .

       -l     use a long listing format

       -h, --human-readable
              with -l and -s, print sizes like 1K 234M 2G etc.

       -R, --recursive
              list subdirectories recursively

NAME
       grep - print lines that match patterns

DESCRIPTION
       grep searches for PATTERNS in each FILE.

       -i, --ignore-case
              Ignore case distinctions in patterns and input data.

       -v, --invert-match
              Invert the sense of matching, to select non-matching lines.

       -r, --recursive
              Read all files under each directory, recursively.
"""


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def collect_corpus(
    max_man_per_section: int = 200,
    max_doc_files: int = 2000,
    max_info_pages: int = 50,
    verbose: bool = True,
) -> str:
    """
    Collect all available Linux documentation.
    Returns a single concatenated string ready for tokenisation.
    """
    parts: list[str] = []

    if verbose:
        print("  [1/4] man pages …")
    man_text = collect_man_pages(max_per_section=max_man_per_section, verbose=verbose)
    if man_text:
        parts.append(man_text)

    if verbose:
        print("  [2/4] /usr/share/doc/ files …")
    doc_text = collect_doc_files(max_files=max_doc_files, verbose=verbose)
    if doc_text:
        parts.append(doc_text)

    if verbose:
        print("  [3/4] GNU info pages …")
    info_text = collect_info_pages(max_files=max_info_pages, verbose=verbose)
    if info_text:
        parts.append(info_text)

    if verbose:
        print("  [4/4] /etc/ config files …")
    etc_text = collect_etc_files(verbose=verbose)
    if etc_text:
        parts.append(etc_text)

    if not parts:
        if verbose:
            print("  WARNING: no sources found, using built-in fallback corpus")
        return FALLBACK_CORPUS

    full = "\n\n".join(parts)
    if verbose:
        print(f"  total corpus size: {len(full):,} chars ({len(full)//1024} KB)")
    return full


# ---------------------------------------------------------------------------
# Dataset
# ---------------------------------------------------------------------------

class TokenDataset:
    """Tokenised text split into overlapping context windows."""

    def __init__(self, token_ids: list[int], context_len: int) -> None:
        self.ids = np.array(token_ids, dtype=np.int32)
        self.T = context_len

    def __len__(self) -> int:
        return max(0, len(self.ids) - self.T - 1)

    def __getitem__(self, i: int) -> tuple[np.ndarray, np.ndarray]:
        i = i % max(1, len(self))
        x = self.ids[i : i + self.T]
        y = self.ids[i + 1 : i + 1 + self.T]
        if len(x) < self.T:
            x = np.pad(x, (0, self.T - len(x)))
            y = np.pad(y, (0, self.T - len(y)))
        return x, y

    def random_batch(self, batch_size: int, rng: random.Random) -> tuple[np.ndarray, np.ndarray]:
        n = max(1, len(self))
        indices = [rng.randint(0, n - 1) for _ in range(batch_size)]
        xs = np.stack([self[i][0] for i in indices])
        ys = np.stack([self[i][1] for i in indices])
        return xs, ys


def train_val_split(ids: list[int], val_frac: float = 0.05) -> tuple[list[int], list[int]]:
    cut = int(len(ids) * (1 - val_frac))
    return ids[:cut], ids[cut:]
