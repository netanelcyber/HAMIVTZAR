"""
Data pipeline: collect Linux man-page text and prepare batches.

Uses `man` (available on any Linux system with man-db) to read actual
documentation pages. Falls back to a small built-in corpus if man is
unavailable in the current environment.
"""

import subprocess
import random
import numpy as np
from pathlib import Path


LINUX_MANPAGES = [
    "ls", "cp", "mv", "rm", "mkdir", "rmdir", "chmod", "chown", "ln",
    "cat", "less", "head", "tail", "grep", "sed", "awk", "sort", "uniq",
    "find", "xargs", "tar", "gzip", "bzip2", "zip", "diff", "patch",
    "ps", "top", "kill", "jobs", "fg", "bg", "nohup", "screen",
    "ssh", "scp", "rsync", "curl", "wget", "ping", "netstat", "ifconfig",
    "mount", "umount", "df", "du", "free", "vmstat", "iostat",
    "echo", "printf", "read", "test", "expr", "date", "sleep",
    "bash", "sh", "env", "export", "source", "alias", "which", "whereis",
    "man", "info", "help", "apropos", "whatis",
    "gcc", "make", "git", "vim", "nano", "emacs",
    "python3", "perl", "awk",
    "cron", "crontab", "systemctl", "journalctl", "dmesg",
    "useradd", "userdel", "passwd", "su", "sudo",
    "iptables", "ufw", "firewalld",
    "dd", "fdisk", "mkfs", "fsck", "lsblk",
    "strace", "ltrace", "gdb", "valgrind",
]

FALLBACK_CORPUS = """\
NAME
       ls - list directory contents

SYNOPSIS
       ls [OPTION]... [FILE]...

DESCRIPTION
       List information about the FILEs (the current directory by default).
       Sort entries alphabetically if none of -cftuvSUX nor --sort is specified.

       Mandatory arguments to long options are mandatory for short options too.

       -a, --all
              do not ignore entries starting with .

       -l     use a long listing format

       -h, --human-readable
              with -l and -s, print sizes like 1K 234M 2G etc.

       -R, --recursive
              list subdirectories recursively

       -t     sort by modification time, newest first

       -S     sort by file size, largest first

NAME
       grep - print lines that match patterns

SYNOPSIS
       grep [OPTION...] PATTERNS [FILE...]

DESCRIPTION
       grep  searches  for  PATTERNS  in  each  FILE.   PATTERNS is one or
       more patterns separated by newline characters, and grep prints  each
       line that matches a pattern.

       -i, --ignore-case
              Ignore case distinctions in patterns and input data.

       -v, --invert-match
              Invert the sense of matching, to select non-matching lines.

       -r, --recursive
              Read all files under each directory, recursively.

       -n, --line-number
              Prefix each line of output with the 1-based line number.

       -c, --count
              Suppress normal output; instead print a count of matching
              lines for each input file.

NAME
       find - search for files in a directory hierarchy

SYNOPSIS
       find [-H] [-L] [-P] [-D debugopts] [-Olevel] [starting-point...] [expression]

DESCRIPTION
       This  manual  page  documents  the  GNU version of find.  GNU find
       searches the directory tree rooted at each given file name  by  evaluating
       the  given  expression  from  left  to right.

       -name pattern
              Base of file name (the path with the leading directories removed)
              matches shell pattern pattern.

       -type c
              File is of type c: f for regular file, d for directory,
              l for symbolic link.

       -mtime n
              File's data was last modified less than, more than or exactly
              n*24 hours ago.

       -exec command ;
              Execute command; true if 0 status is returned.
"""


def fetch_manpage(cmd: str) -> str:
    """Return plain-text man page for *cmd*, or empty string on failure."""
    try:
        result = subprocess.run(
            ["man", cmd],
            capture_output=True, text=True, timeout=5,
            env={"MANPAGER": "cat", "TERM": "dumb", "PATH": "/usr/bin:/bin"},
        )
        return result.stdout
    except Exception:
        return ""


def collect_corpus(max_pages: int = 30) -> str:
    """Fetch up to *max_pages* man pages; fall back to built-in corpus."""
    pages = []
    for cmd in LINUX_MANPAGES[:max_pages]:
        text = fetch_manpage(cmd)
        if text.strip():
            pages.append(text)

    if not pages:
        return FALLBACK_CORPUS

    return "\n\n".join(pages)


# ---------------------------------------------------------------------------
# Dataset
# ---------------------------------------------------------------------------

class TokenDataset:
    """Tokenised text split into overlapping context windows."""

    def __init__(
        self,
        token_ids: list[int],
        context_len: int,
    ) -> None:
        self.ids = np.array(token_ids, dtype=np.int32)
        self.T = context_len

    def __len__(self) -> int:
        return max(0, len(self.ids) - self.T - 1)

    def __getitem__(self, i: int) -> tuple[np.ndarray, np.ndarray]:
        i = i % max(1, len(self))
        x = self.ids[i : i + self.T]
        y = self.ids[i + 1 : i + 1 + self.T]
        # pad to context_len if near end
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


def train_val_split(
    ids: list[int], val_frac: float = 0.1
) -> tuple[list[int], list[int]]:
    cut = int(len(ids) * (1 - val_frac))
    return ids[:cut], ids[cut:]
