#!/usr/bin/env python3
"""
kvm_p2p.py - KVM/QEMU OS auto-downloader + launcher.

Install:
  pip install --break-system-packages fastapi uvicorn aiohttp websockets
  sudo apt-get install aria2 qemu-system-x86 qemu-utils xz-utils cloud-image-utils novnc genisoimage xorriso openssl

Run:
  python3 kvm_p2p.py server --port 8765
  open http://127.0.0.1:8765/client
"""

from __future__ import annotations

import argparse
import base64
import asyncio
import hashlib
import json
import lzma
import os
import re
import shutil
import secrets
import signal
import socket
import subprocess
import sys
import time
import uuid
import webbrowser
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Keep WebSocket resolvable in module globals so FastAPI can evaluate the
# string annotation produced by `from __future__ import annotations`.
try:
    from fastapi import WebSocket  # type: ignore
except Exception:  # pragma: no cover
    WebSocket = Any  # type: ignore

try:
    import aiohttp
except Exception:  # pragma: no cover
    aiohttp = None

APP_NAME = "kvm-p2p"
DEFAULT_DATA_DIR = Path(os.environ.get("KVM_P2P_HOME", str(Path.home() / ".local" / "share" / APP_NAME))).expanduser()
DATA_DIR = DEFAULT_DATA_DIR
IMAGES_DIR = DATA_DIR / "images"
VMS_DIR = DATA_DIR / "vms"
LOGS_DIR = DATA_DIR / "logs"

BIND_HOST = os.environ.get("KVM_BIND_HOST", "127.0.0.1")

DOWNLOADS: Dict[str, Dict[str, Any]] = {}
DOWNLOAD_TASKS: Dict[str, asyncio.Task] = {}
PROVISION: Dict[str, Dict[str, Any]] = {}
VM_PROCS: Dict[str, subprocess.Popen] = {}
RUNNING_VMS: Dict[str, Dict[str, Any]] = {}


def _dirs() -> None:
    for p in (DATA_DIR, IMAGES_DIR, VMS_DIR, LOGS_DIR):
        p.mkdir(parents=True, exist_ok=True)


@dataclass
class ImageItem:
    id: str
    name: str
    family: str
    distro: str
    arch: str
    kind: str
    file_name: str
    mirrors: List[str] = field(default_factory=list)
    checksum_url: Optional[str] = None
    checksum_name: Optional[str] = None
    checksum_algo: str = "sha256"
    needs_browser: bool = False
    browser_url: Optional[str] = None
    notes: str = ""

    def public(self) -> Dict[str, Any]:
        path = local_image_path(self)
        return {
            "aria2c": have_aria2c(),
            "id": self.id,
            "name": self.name,
            "family": self.family,
            "distro": self.distro,
            "arch": self.arch,
            "kind": self.kind,
            "file_name": self.file_name,
            "mirror_count": len(self.mirrors),
            "needs_browser": self.needs_browser,
            "browser_url": self.browser_url,
            "downloaded": path.exists(),
            "path": str(path) if path.exists() else None,
            "checksum": bool(self.checksum_url),
            "launchable": self.kind in ("cloud", "iso") and self.family in ("linux", "windows", "bsd"),
            "notes": self.notes,
        }


CATALOG: List[ImageItem] = [
    ImageItem(
        id="ubuntu-24.04",
        name="Ubuntu Server 24.04 LTS cloud image",
        family="linux", distro="ubuntu", arch="x86_64", kind="cloud",
        file_name="ubuntu-24.04-server-cloudimg-amd64.img",
        mirrors=[
            "https://cloud-images.ubuntu.com/noble/current/noble-server-cloudimg-amd64.img",
            "https://cloud-images.ubuntu.com/releases/24.04/release/ubuntu-24.04-server-cloudimg-amd64.img",
        ],
        checksum_url="https://cloud-images.ubuntu.com/noble/current/SHA256SUMS",
        checksum_name="noble-server-cloudimg-amd64.img",
    ),
    ImageItem(
        id="ubuntu-22.04",
        name="Ubuntu Server 22.04 LTS cloud image",
        family="linux", distro="ubuntu", arch="x86_64", kind="cloud",
        file_name="ubuntu-22.04-server-cloudimg-amd64.img",
        mirrors=[
            "https://cloud-images.ubuntu.com/jammy/current/jammy-server-cloudimg-amd64.img",
            "https://cloud-images.ubuntu.com/releases/22.04/release/ubuntu-22.04-server-cloudimg-amd64.img",
        ],
        checksum_url="https://cloud-images.ubuntu.com/jammy/current/SHA256SUMS",
        checksum_name="jammy-server-cloudimg-amd64.img",
    ),
    ImageItem(
        id="ubuntu-24.04-desktop",
        name="Ubuntu Desktop 24.04 LTS ISO",
        family="linux", distro="ubuntu", arch="x86_64", kind="iso",
        file_name="ubuntu-24.04-desktop-amd64.iso",
        mirrors=[
            "https://releases.ubuntu.com/24.04/ubuntu-24.04.4-desktop-amd64.iso",
            "https://mirrors.edge.kernel.org/ubuntu-releases/24.04/ubuntu-24.04.4-desktop-amd64.iso",
        ],
        checksum_url="https://releases.ubuntu.com/24.04/SHA256SUMS",
        checksum_name="ubuntu-24.04.4-desktop-amd64.iso",
    ),
    ImageItem(
        id="ubuntu-24.04-server-iso",
        name="Ubuntu Server 24.04.4 live server ISO",
        family="linux", distro="ubuntu", arch="x86_64", kind="iso",
        file_name="ubuntu-24.04.4-live-server-amd64.iso",
        mirrors=[
            "https://releases.ubuntu.com/24.04/ubuntu-24.04.4-live-server-amd64.iso",
            "https://mirrors.edge.kernel.org/ubuntu-releases/24.04/ubuntu-24.04.4-live-server-amd64.iso",
        ],
        checksum_url="https://releases.ubuntu.com/24.04/SHA256SUMS",
        checksum_name="ubuntu-24.04.4-live-server-amd64.iso",
        notes="Supports Ubuntu Subiquity autoinstall from a generated NoCloud seed when xorriso is installed.",
    ),
    ImageItem(
        id="debian-13",
        name="Debian 13 Trixie genericcloud qcow2",
        family="linux", distro="debian", arch="x86_64", kind="cloud",
        file_name="debian-13-genericcloud-amd64.qcow2",
        mirrors=[
            "https://cloud.debian.org/images/cloud/trixie/latest/debian-13-genericcloud-amd64.qcow2",
            "https://cdimage.debian.org/cdimage/cloud/trixie/latest/debian-13-genericcloud-amd64.qcow2",
        ],
        checksum_url="https://cloud.debian.org/images/cloud/trixie/latest/SHA512SUMS",
        checksum_name="debian-13-genericcloud-amd64.qcow2",
        checksum_algo="sha512",
    ),
    ImageItem(
        id="debian-13-netinst",
        name="Debian 13.5 Trixie netinst ISO",
        family="linux", distro="debian", arch="x86_64", kind="iso",
        file_name="debian-13.5.0-amd64-netinst.iso",
        mirrors=[
            "https://cdimage.debian.org/debian-cd/current/amd64/iso-cd/debian-13.5.0-amd64-netinst.iso",
            "https://mirrors.edge.kernel.org/debian-cd/current/amd64/iso-cd/debian-13.5.0-amd64-netinst.iso",
        ],
        checksum_url="https://cdimage.debian.org/debian-cd/current/amd64/iso-cd/SHA512SUMS",
        checksum_name="debian-13.5.0-amd64-netinst.iso",
        checksum_algo="sha512",
    ),
    ImageItem(
        id="fedora-cloud",
        name="Fedora Cloud Base 44 qcow2",
        family="linux", distro="fedora", arch="x86_64", kind="cloud",
        file_name="Fedora-Cloud-Base-Generic-44-1.7.x86_64.qcow2",
        mirrors=[
            "https://download.fedoraproject.org/pub/fedora/linux/releases/44/Cloud/x86_64/images/Fedora-Cloud-Base-Generic-44-1.7.x86_64.qcow2",
            "https://dl.fedoraproject.org/pub/fedora/linux/releases/44/Cloud/x86_64/images/Fedora-Cloud-Base-Generic-44-1.7.x86_64.qcow2",
        ],
        checksum_url="https://download.fedoraproject.org/pub/fedora/linux/releases/44/Cloud/x86_64/images/Fedora-Cloud-44-1.7-x86_64-CHECKSUM",
        checksum_name="Fedora-Cloud-Base-Generic-44-1.7.x86_64.qcow2",
    ),
    ImageItem(
        id="fedora-server-netinst",
        name="Fedora Server 44 netinst ISO",
        family="linux", distro="fedora", arch="x86_64", kind="iso",
        file_name="Fedora-Server-netinst-x86_64-44-1.7.iso",
        mirrors=[
            "https://download.fedoraproject.org/pub/fedora/linux/releases/44/Server/x86_64/iso/Fedora-Server-netinst-x86_64-44-1.7.iso",
            "https://dl.fedoraproject.org/pub/fedora/linux/releases/44/Server/x86_64/iso/Fedora-Server-netinst-x86_64-44-1.7.iso",
        ],
        checksum_url="https://download.fedoraproject.org/pub/fedora/linux/releases/44/Server/x86_64/iso/Fedora-Server-44-1.7-x86_64-CHECKSUM",
        checksum_name="Fedora-Server-netinst-x86_64-44-1.7.iso",
    ),
    ImageItem(
        id="alpine-virt",
        name="Alpine Linux virt ISO",
        family="linux", distro="alpine", arch="x86_64", kind="iso",
        file_name="alpine-virt-x86_64.iso",
        mirrors=[
            "https://dl-cdn.alpinelinux.org/alpine/latest-stable/releases/x86_64/alpine-virt-latest-x86_64.iso",
            "https://dl-2.alpinelinux.org/alpine/latest-stable/releases/x86_64/alpine-virt-latest-x86_64.iso",
        ],
    ),
    ImageItem(
        id="archlinux",
        name="Arch Linux ISO latest",
        family="linux", distro="arch", arch="x86_64", kind="iso",
        file_name="archlinux-x86_64.iso",
        mirrors=[
            "https://geo.mirror.pkgbuild.com/iso/latest/archlinux-x86_64.iso",
            "https://mirror.rackspace.com/archlinux/iso/latest/archlinux-x86_64.iso",
        ],
        checksum_url="https://geo.mirror.pkgbuild.com/iso/latest/sha256sums.txt",
        checksum_name="archlinux-x86_64.iso",
    ),
    ImageItem(
        id="kali-installer",
        name="Kali Linux installer ISO current",
        family="linux", distro="kali", arch="x86_64", kind="iso",
        file_name="kali-linux-installer-amd64.iso",
        mirrors=[
            "https://cdimage.kali.org/current/kali-linux-installer-amd64.iso",
        ],
        notes="Kali current filenames may change; update the URL from cdimage.kali.org/current/.",
    ),
    ImageItem(
        id="freebsd-14",
        name="FreeBSD 14.3 RELEASE qcow2.xz",
        family="bsd", distro="freebsd", arch="x86_64", kind="cloud",
        file_name="FreeBSD-14.3-RELEASE-amd64.qcow2.xz",
        mirrors=[
            "https://download.freebsd.org/releases/VM-IMAGES/14.3-RELEASE/amd64/Latest/FreeBSD-14.3-RELEASE-amd64.qcow2.xz",
            "https://ftp.freebsd.org/pub/FreeBSD/releases/VM-IMAGES/14.3-RELEASE/amd64/Latest/FreeBSD-14.3-RELEASE-amd64.qcow2.xz",
        ],
    ),
    ImageItem(
        id="win-server-2025",
        name="Windows Server 2025 Evaluation ISO",
        family="windows", distro="windows-server", arch="x86_64", kind="iso",
        file_name="windows-server-2025-eval.iso",
        mirrors=["https://go.microsoft.com/fwlink/?clcid=0x409&country=us&culture=en-us&linkid=2345730"],
        browser_url="https://www.microsoft.com/en-us/evalcenter/download-windows-server-2025",
        notes="Microsoft evaluation download. The fwlink may rotate; use browser fallback if it fails.",
    ),
    ImageItem(
        id="win-server-2022",
        name="Windows Server 2022 Evaluation ISO",
        family="windows", distro="windows-server", arch="x86_64", kind="iso",
        file_name="windows-server-2022-eval.iso",
        mirrors=["https://go.microsoft.com/fwlink/p/?LinkID=2195280&clcid=0x409&country=US&culture=en-us"],
        browser_url="https://www.microsoft.com/en-us/evalcenter/download-windows-server-2022",
        notes="Microsoft evaluation download. The fwlink may rotate; use browser fallback if it fails.",
    ),
    ImageItem(
        id="virtio-win",
        name="Windows VirtIO drivers ISO",
        family="windows", distro="virtio", arch="x86_64", kind="drivers",
        file_name="virtio-win.iso",
        mirrors=[
            "https://fedorapeople.org/groups/virt/virtio-win/direct-downloads/latest-virtio/virtio-win.iso",
        ],
    ),
    ImageItem(
        id="win11-enterprise-eval",
        name="Windows 11 Enterprise Evaluation",
        family="windows", distro="windows-client", arch="x86_64", kind="manual",
        file_name="windows-11-enterprise-eval.iso",
        needs_browser=True,
        browser_url="https://www.microsoft.com/en-us/evalcenter/download-windows-11-enterprise",
        notes="Requires Microsoft form/browser flow. Download manually, place ISO in images/ with this file name.",
    ),
]

CAT_BY_ID = {x.id: x for x in CATALOG}


def local_image_path(img: ImageItem) -> Path:
    p = IMAGES_DIR / img.file_name
    if img.file_name.endswith(".xz"):
        unxz = IMAGES_DIR / img.file_name[:-3]
        if unxz.exists():
            return unxz
    return p


def stored_download_path(img: ImageItem) -> Path:
    return IMAGES_DIR / img.file_name


def have_aria2c() -> bool:
    return shutil.which("aria2c") is not None


def now() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")


def status_init(image_id: str) -> Dict[str, Any]:
    st = DOWNLOADS.setdefault(image_id, {})
    st.update({
        "id": image_id,
        "progress": 0.0,
        "phase": "queued",
        "sha256_verified": False,
        "checksum_verified": False,
        "checksum_algo": None,
        "downloaded": False,
        "total": None,
        "downloaded_bytes": 0,
        "engine": "aria2c" if have_aria2c() else "aiohttp",
        "message": "queued",
        "updated_at": now(),
    })
    return st


def status_update(image_id: str, **kwargs: Any) -> None:
    st = DOWNLOADS.setdefault(image_id, {"id": image_id})
    st.update(kwargs)
    st["updated_at"] = now()


async def http_head_total(url: str, timeout: int = 20) -> Optional[int]:
    if aiohttp is None:
        return None
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout)) as session:
            async with session.head(url, allow_redirects=True) as resp:
                if 200 <= resp.status < 400:
                    val = resp.headers.get("Content-Length")
                    return int(val) if val and val.isdigit() else None
    except Exception:
        return None
    return None


async def fetch_text(url: str, timeout: int = 30) -> str:
    if aiohttp is None:
        raise RuntimeError("aiohttp is not installed")
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout)) as session:
        async with session.get(url, allow_redirects=True) as resp:
            resp.raise_for_status()
            return await resp.text()


def compute_digest(path: Path, algo: str) -> str:
    h = hashlib.new(algo)
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


async def verify_checksum(img: ImageItem, path: Path) -> bool:
    if not img.checksum_url:
        status_update(img.id, checksum_algo=None, message="no upstream checksum configured")
        return False
    algo = img.checksum_algo.lower()
    try:
        text = await fetch_text(img.checksum_url)
        needle = img.checksum_name or Path(img.mirrors[0]).name or path.name
        expected = None
        for line in text.splitlines():
            if needle in line:
                m = re.search(r"\b([a-fA-F0-9]{64}|[a-fA-F0-9]{128})\b", line)
                if m:
                    expected = m.group(1).lower()
                    break
        if not expected:
            status_update(img.id, phase="verify", message=f"checksum entry not found for {needle}", checksum_algo=algo)
            return False
        got = compute_digest(path, algo).lower()
        ok = got == expected
        status_update(
            img.id,
            phase="verify",
            checksum_verified=ok,
            sha256_verified=ok if algo == "sha256" else DOWNLOADS.get(img.id, {}).get("sha256_verified", False),
            checksum_algo=algo,
            message=f"{algo} {'ok' if ok else 'mismatch'}",
        )
        if not ok:
            raise RuntimeError(f"{algo} mismatch for {img.id}: got {got}, expected {expected}")
        return True
    except Exception as e:
        status_update(img.id, phase="verify", message=f"checksum failed: {e}", checksum_algo=algo)
        raise


async def download_with_aiohttp(img: ImageItem, url: str, dest: Path) -> None:
    if aiohttp is None:
        raise RuntimeError("aiohttp is not installed. pip install aiohttp")
    existing = dest.stat().st_size if dest.exists() else 0
    headers: Dict[str, str] = {"User-Agent": "kvm-p2p/1.0"}
    if existing > 0:
        headers["Range"] = f"bytes={existing}-"
    timeout = aiohttp.ClientTimeout(total=None, sock_connect=30, sock_read=60)
    async with aiohttp.ClientSession(timeout=timeout, headers={"User-Agent": "kvm-p2p/1.0"}) as session:
        async with session.get(url, headers=headers, allow_redirects=True) as resp:
            if resp.status == 416:
                return
            if resp.status not in (200, 206):
                raise RuntimeError(f"HTTP {resp.status}")
            mode = "ab" if resp.status == 206 and existing else "wb"
            total_hdr = resp.headers.get("Content-Length")
            if total_hdr and total_hdr.isdigit():
                total = int(total_hdr) + (existing if mode == "ab" else 0)
            else:
                total = None
            done = existing if mode == "ab" else 0
            status_update(img.id, phase="download", total=total, downloaded_bytes=done, message=f"aiohttp {url}")
            with dest.open(mode) as f:
                async for chunk in resp.content.iter_chunked(1024 * 1024):
                    if not chunk:
                        continue
                    f.write(chunk)
                    done += len(chunk)
                    progress = (done / total * 100.0) if total else 0.0
                    status_update(img.id, phase="download", progress=round(min(progress, 100.0), 2), downloaded_bytes=done, total=total)


async def download_with_aria2c(img: ImageItem, url: str, dest: Path) -> None:
    total = await http_head_total(url)
    cmd = [
        "aria2c",
        "--continue=true",
        "--max-connection-per-server=16",
        "--split=16",
        "--min-split-size=1M",
        "--timeout=20",
        "--max-tries=2",
        "--retry-wait=3",
        "--allow-overwrite=true",
        "--auto-file-renaming=false",
        "-d", str(dest.parent),
        "-o", dest.name,
        url,
    ]
    log_path = LOGS_DIR / f"download-{img.id}.log"
    status_update(img.id, phase="download", total=total, engine="aria2c", message=f"aria2c {url}")
    with log_path.open("ab") as log:
        proc = subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT)
        while proc.poll() is None:
            done = dest.stat().st_size if dest.exists() else 0
            progress = (done / total * 100.0) if total else 0.0
            status_update(img.id, progress=round(min(progress, 100.0), 2), downloaded_bytes=done, total=total)
            await asyncio.sleep(1.0)
        if proc.returncode != 0:
            raise RuntimeError(f"aria2c failed with exit {proc.returncode}; see {log_path}")
    done = dest.stat().st_size if dest.exists() else 0
    status_update(img.id, progress=100.0 if done else 0.0, downloaded_bytes=done, total=total)


def decompress_xz(src: Path, dst: Path, image_id: str) -> None:
    status_update(image_id, phase="unxz", message=f"decompressing {src.name}")
    tmp = dst.with_suffix(dst.suffix + ".tmp")
    done = 0
    with lzma.open(src, "rb") as inp, tmp.open("wb") as out:
        while True:
            chunk = inp.read(1024 * 1024)
            if not chunk:
                break
            out.write(chunk)
            done += len(chunk)
            status_update(image_id, phase="unxz", message=f"wrote {done} bytes")
    tmp.replace(dst)
    status_update(image_id, phase="unxz", message=f"unpacked to {dst.name}")


async def ensure_download(image_id: str) -> Path:
    _dirs()
    img = CAT_BY_ID.get(image_id)
    if not img:
        raise KeyError(f"unknown image id: {image_id}")
    if img.needs_browser:
        if img.browser_url:
            try:
                webbrowser.open(img.browser_url)
            except Exception:
                pass
        status_update(image_id, phase="manual", message="manual browser download required", downloaded=local_image_path(img).exists())
        raise RuntimeError(f"manual download required: {img.browser_url}")
    final_path = local_image_path(img)
    if final_path.exists():
        status_update(image_id, phase="done", progress=100.0, downloaded=True, message="already downloaded", downloaded_bytes=final_path.stat().st_size)
        return final_path
    status_init(image_id)
    dest = stored_download_path(img)
    last_err = None
    for url in img.mirrors:
        try:
            status_update(image_id, phase="download", message=f"trying {url}")
            if have_aria2c():
                await download_with_aria2c(img, url, dest)
            else:
                await download_with_aiohttp(img, url, dest)
            if not dest.exists() or dest.stat().st_size == 0:
                raise RuntimeError("download produced empty file")
            if img.checksum_url:
                await verify_checksum(img, dest)
            if dest.name.endswith(".xz"):
                out = IMAGES_DIR / dest.name[:-3]
                decompress_xz(dest, out, image_id)
                final_path = out
            else:
                final_path = dest
            status_update(image_id, phase="done", progress=100.0, downloaded=True, message=f"ready: {final_path}", downloaded_bytes=final_path.stat().st_size)
            return final_path
        except Exception as e:
            last_err = e
            status_update(image_id, phase="retry", message=f"mirror failed: {e}")
            await asyncio.sleep(0.5)
    status_update(image_id, phase="error", message=str(last_err), downloaded=False)
    if img.browser_url:
        status_update(image_id, browser_url=img.browser_url)
    raise RuntimeError(f"all mirrors failed for {image_id}: {last_err}")


def find_free_port(start: int = 20000, end: int = 65000) -> int:
    for port in range(start, end):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    raise RuntimeError("no free localhost port found")


def qemu_img_format(path: Path) -> str:
    if shutil.which("qemu-img"):
        try:
            out = subprocess.check_output(["qemu-img", "info", "--output=json", str(path)], text=True, stderr=subprocess.DEVNULL)
            fmt = json.loads(out).get("format")
            if fmt:
                return fmt
        except Exception:
            pass
    return "qcow2" if path.suffix.lower() == ".qcow2" else "raw"


def qemu_supports_audiodev_none(qemu: str) -> bool:
    try:
        subprocess.check_output([qemu, "-audiodev", "help"], text=True, stderr=subprocess.STDOUT, timeout=5)
        return True
    except Exception:
        return False


def qemu_child_env() -> Dict[str, str]:
    env = os.environ.copy()
    env.setdefault("QEMU_AUDIO_DRV", "none")
    env.setdefault("SDL_AUDIODRIVER", "dummy")
    env.setdefault("PIPEWIRE_NO_CONFIG", "1")
    return env


def yaml_quote(value: Any) -> str:
    return json.dumps(str(value))


def linux_default_password() -> str:
    return "P@ssw0rd-" + secrets.token_hex(4)


def sanitize_linux_username(value: Optional[str]) -> str:
    user = (value or "qemu").strip().lower()
    user = re.sub(r"[^a-z0-9_-]", "-", user)
    user = re.sub(r"^[^a-z_]+", "", user)
    return (user or "qemu")[:32]


def sanitize_hostname(value: Optional[str], fallback: str = "kvm-linux") -> str:
    host = (value or fallback).strip().lower()
    host = re.sub(r"[^a-z0-9-]", "-", host)
    host = re.sub(r"-+", "-", host).strip("-")
    return (host or fallback)[:63]


def sanitize_linux_repo_profile(value: Optional[str]) -> str:
    profile = (value or "global").strip().lower()
    aliases = {
        "default": "global", "world": "global", "global": "global", "official": "global",
        "israel": "israel", "il": "israel", "isoc": "israel",
        "none": "none", "off": "none", "false": "none",
    }
    return aliases.get(profile, "global")


def _indent_yaml_literal(text: str, spaces: int = 6) -> str:
    pad = " " * spaces
    return "\n".join((pad + line) if line else pad for line in text.splitlines())


def build_linux_repo_inject_bash(repo_profile: str = "global", update: bool = True, fix_dns: bool = True) -> str:
    profile = sanitize_linux_repo_profile(repo_profile)
    script = r"""#!/usr/bin/env bash
set -Eeuo pipefail
PROFILE="__PROFILE__"
DO_UPDATE="__DO_UPDATE__"
FIX_DNS="__FIX_DNS__"
LOG="/var/log/kvm-p2p-repo-inject.log"
mkdir -p /var/log
exec > >(tee -a "$LOG") 2>&1 || true
say() { printf '[%s] %s\n' "$(date '+%F %T')" "$*"; }
load_os() {
  ID="unknown"; VERSION_ID=""; VERSION_CODENAME=""; ID_LIKE=""
  [ -r /etc/os-release ] && . /etc/os-release
  ID="${ID:-unknown}"; VERSION_ID="${VERSION_ID:-}"
  VERSION_CODENAME="${VERSION_CODENAME:-${UBUNTU_CODENAME:-}}"; ID_LIKE="${ID_LIKE:-}"
}
maybe_fix_dns() {
  [ "$FIX_DNS" = "1" ] || return 0
  command -v getent >/dev/null 2>&1 && getent hosts deb.debian.org >/dev/null 2>&1 && { say "DNS works"; return 0; }
  say "injecting fallback DNS"
  [ -L /etc/resolv.conf ] && rm -f /etc/resolv.conf
  printf 'nameserver 1.1.1.1\nnameserver 8.8.8.8\noptions timeout:2 attempts:3\n' >/etc/resolv.conf
}
inject_apt() {
  local codename="${VERSION_CODENAME:-}"
  [ -n "$codename" ] || { say "cannot determine apt codename"; return 1; }
  local ubuntu_mirror="http://archive.ubuntu.com/ubuntu"
  local debian_mirror="http://deb.debian.org/debian"
  [ "$PROFILE" = "israel" ] && ubuntu_mirror="http://mirror.isoc.org.il/pub/ubuntu" && debian_mirror="http://mirror.isoc.org.il/pub/debian"
  if [ "$ID" = "ubuntu" ] || echo "$ID_LIKE" | grep -qi ubuntu; then
    say "writing Ubuntu apt repos: $codename"
    cat >/etc/apt/sources.list.d/kvm-p2p.sources <<EOF
Types: deb
URIs: $ubuntu_mirror
Suites: $codename $codename-updates $codename-backports
Components: main restricted universe multiverse
Signed-By: /usr/share/keyrings/ubuntu-archive-keyring.gpg

Types: deb
URIs: http://security.ubuntu.com/ubuntu
Suites: $codename-security
Components: main restricted universe multiverse
Signed-By: /usr/share/keyrings/ubuntu-archive-keyring.gpg
EOF
  else
    say "writing Debian apt repos: $codename"
    cat >/etc/apt/sources.list.d/kvm-p2p.sources <<EOF
Types: deb
URIs: $debian_mirror
Suites: $codename $codename-updates
Components: main contrib non-free non-free-firmware
Signed-By: /usr/share/keyrings/debian-archive-keyring.gpg
EOF
  fi
  sed -i 's/^[[:space:]]*deb /# disabled by kvm-p2p: deb /' /etc/apt/sources.list 2>/dev/null || true
  [ "$DO_UPDATE" = "1" ] && apt-get update || true
}
main() {
  [ "$PROFILE" = "none" ] && { say "repo injection disabled"; exit 0; }
  load_os
  say "repo injection start: ID=$ID VERSION_ID=$VERSION_ID PROFILE=$PROFILE"
  maybe_fix_dns
  if command -v apt-get >/dev/null 2>&1; then inject_apt
  elif command -v dnf >/dev/null 2>&1 || command -v yum >/dev/null 2>&1; then
    say "dnf/yum: using distro metalinks (no injection needed for Fedora/RHEL)"
    [ "$DO_UPDATE" = "1" ] && (dnf -y makecache 2>/dev/null || yum -y makecache 2>/dev/null) || true
  elif command -v pacman >/dev/null 2>&1; then
    [ "$DO_UPDATE" = "1" ] && pacman -Syy --noconfirm || true
  elif command -v apk >/dev/null 2>&1; then
    [ "$DO_UPDATE" = "1" ] && apk update || true
  fi
  say "repo injection done"
}
main "$@"
"""
    return (script
            .replace("__PROFILE__", profile)
            .replace("__DO_UPDATE__", "1" if update else "0")
            .replace("__FIX_DNS__", "1" if fix_dns else "0"))


def build_repo_cloud_init_blocks(inject_repos: bool, repo_profile: str, repo_update: bool, repo_fix_dns: bool) -> Tuple[str, str]:
    if not inject_repos or sanitize_linux_repo_profile(repo_profile) == "none":
        return "", ""
    script = build_linux_repo_inject_bash(repo_profile, repo_update, repo_fix_dns)
    write_files = f"""write_files:
  - path: /usr/local/sbin/kvm-p2p-inject-repos.sh
    owner: root:root
    permissions: '0755'
    content: |
{_indent_yaml_literal(script, 6)}
"""
    runcmd = "  - [ bash, /usr/local/sbin/kvm-p2p-inject-repos.sh ]\n"
    return write_files, runcmd


def build_linux_cloud_init_user_data(
    username: str, password: str, hostname: str,
    ssh_public_key: Optional[str] = None,
    inject_repos: bool = False, repo_profile: str = "global",
    repo_update: bool = True, repo_fix_dns: bool = True,
) -> str:
    username = sanitize_linux_username(username)
    hostname = sanitize_hostname(hostname)
    ssh_keys = f"    ssh_authorized_keys:\n      - {yaml_quote(ssh_public_key.strip())}\n" if ssh_public_key else ""
    repo_write_files, repo_runcmd = build_repo_cloud_init_blocks(inject_repos, repo_profile, repo_update, repo_fix_dns)
    return f"""#cloud-config
hostname: {yaml_quote(hostname)}
manage_etc_hosts: true
users:
  - default
  - name: {yaml_quote(username)}
    gecos: {yaml_quote(username)}
    groups: [adm, sudo]
    shell: /bin/bash
    sudo: ALL=(ALL) NOPASSWD:ALL
    lock_passwd: false
{ssh_keys}ssh_pwauth: true
disable_root: false
chpasswd:
  expire: false
  list: |
    {username}:{password}
{repo_write_files}packages:
  - qemu-guest-agent
runcmd:
{repo_runcmd}  - [ systemctl, enable, --now, ssh ]
  - [ systemctl, enable, --now, qemu-guest-agent ]
"""


def create_cloud_init_seed(
    vm_dir: Path, username: str = "qemu", password: str = "qemu",
    hostname: str = "kvm-p2p", ssh_public_key: Optional[str] = None,
    inject_repos: bool = False, repo_profile: str = "global",
    repo_update: bool = True, repo_fix_dns: bool = True,
) -> Optional[Path]:
    user_data = vm_dir / "user-data"
    meta_data = vm_dir / "meta-data"
    seed = vm_dir / "seed.iso"
    user_data.write_text(
        build_linux_cloud_init_user_data(username, password, hostname, ssh_public_key, inject_repos, repo_profile, repo_update, repo_fix_dns),
        encoding="utf-8",
    )
    meta_data.write_text(f"instance-id: {uuid.uuid4()}\nlocal-hostname: {sanitize_hostname(hostname)}\n", encoding="utf-8")
    cloud_localds = shutil.which("cloud-localds")
    if cloud_localds:
        subprocess.check_call([cloud_localds, str(seed), str(user_data), str(meta_data)])
        return seed
    iso_builder = find_iso_builder()
    if iso_builder:
        subprocess.check_call(iso_builder + ["-quiet", "-J", "-r", "-V", "CIDATA", "-o", str(seed), str(vm_dir)])
        return seed
    return None


def linux_password_hash(password: str) -> str:
    """Return a SHA-512 crypt hash. Uses openssl (preferred) or hashlib fallback."""
    salt = secrets.token_hex(8)
    openssl = shutil.which("openssl")
    if openssl:
        return subprocess.check_output([openssl, "passwd", "-6", "-salt", salt, password], text=True).strip()
    # hashlib-based SHA-512-crypt (RFC 3655) — no external dependency, works on Python 3.13+
    try:
        import crypt as _crypt  # noqa: PLC0415  # removed in 3.13
        h = _crypt.crypt(password, f"$6${salt}$")
        if h:
            return h
    except (ImportError, AttributeError):
        pass
    # Minimal SHA-512-crypt implementation for environments without openssl or crypt
    def _sha512_crypt(pw: str, salt_str: str) -> str:
        """Simplified SHA-512-crypt sufficient for Subiquity autoinstall."""
        pw_b = pw.encode()
        salt_b = salt_str.encode()
        # Step 1-3
        digest_b = hashlib.sha512(pw_b + salt_b + pw_b).digest()
        # Step 4-8
        s1 = hashlib.sha512(pw_b + salt_b)
        for i in range(len(pw_b)):
            s1.update(digest_b[i % 64:i % 64 + 1])
        i = len(pw_b)
        while i > 0:
            s1.update(digest_b if i >= 64 else digest_b[:i])
            i >>= 1
        digest_a = s1.digest()
        # Step 9-10
        s2 = hashlib.sha512()
        for _ in range(len(pw_b)):
            s2.update(pw_b)
        p_bytes = s2.digest()
        p_str = (p_bytes * ((len(pw_b) // 64) + 1))[:len(pw_b)]
        # Step 11-12
        s3 = hashlib.sha512()
        for _ in range(16 + digest_a[0]):
            s3.update(salt_b)
        s_str = (s3.digest() * ((len(salt_b) // 64) + 1))[:len(salt_b)]
        # Step 13-15: 5000 rounds
        c = digest_a
        for i in range(5000):
            s = hashlib.sha512()
            s.update(p_str if i % 2 else c)
            if i % 3:
                s.update(s_str)
            if i % 7:
                s.update(p_str)
            s.update(c if i % 2 else p_str)
            c = s.digest()
        # Base64 encode in SHA-512-crypt order
        _b64 = "./0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
        def _enc(b2: int, b1: int, b0: int, n: int) -> str:
            v = (b2 << 16) | (b1 << 8) | b0
            return "".join(_b64[(v >> (6 * i)) & 0x3f] for i in range(n))
        order = [(0,21,42),(22,43,1),(44,2,23),(3,24,45),(25,46,4),(47,5,26),(6,27,48),(28,49,7),(50,8,29),(9,30,51),(31,52,10),(53,11,32),(12,33,54),(34,55,13),(56,14,35),(15,36,57),(37,58,16),(59,17,38),(18,39,60),(40,61,19),(62,20,41)]
        result = "".join(_enc(c[a], c[b], c[d], 4) for a, b, d in order)
        result += _enc(0, 0, c[63], 2)
        return f"$6${salt_str}${result}"
    return _sha512_crypt(password, salt)


def build_ubuntu_autoinstall_user_data(
    username: str, password: str, hostname: str,
    ssh_public_key: Optional[str] = None,
    inject_repos: bool = False, repo_profile: str = "global",
    repo_update: bool = True, repo_fix_dns: bool = True,
) -> str:
    username = sanitize_linux_username(username)
    hostname = sanitize_hostname(hostname)
    password_hash = linux_password_hash(password)
    key_block = f"    authorized-keys:\n      - {yaml_quote(ssh_public_key.strip())}\n" if ssh_public_key else ""
    repo_late = ""
    if inject_repos and sanitize_linux_repo_profile(repo_profile) != "none":
        script = build_linux_repo_inject_bash(repo_profile, repo_update, repo_fix_dns)
        b64 = base64.b64encode(script.encode()).decode("ascii")
        cmd = (f"printf %s {b64} | base64 -d > /usr/local/sbin/kvm-p2p-inject-repos.sh && "
               "chmod +x /usr/local/sbin/kvm-p2p-inject-repos.sh && /usr/local/sbin/kvm-p2p-inject-repos.sh")
        repo_late = "    - curtin in-target --target=/target -- bash -lc " + json.dumps(cmd) + "\n"
    return f"""#cloud-config
autoinstall:
  version: 1
  locale: en_US.UTF-8
  keyboard:
    layout: us
  timezone: UTC
  identity:
    hostname: {yaml_quote(hostname)}
    username: {yaml_quote(username)}
    password: {yaml_quote(password_hash)}
  ssh:
    install-server: true
    allow-pw: true
{key_block}  storage:
    layout:
      name: direct
  packages:
    - openssh-server
    - qemu-guest-agent
  late-commands:
{repo_late}    - curtin in-target --target=/target systemctl enable ssh || true
    - curtin in-target --target=/target systemctl enable qemu-guest-agent || true
"""


def find_iso_builder() -> Optional[List[str]]:
    xorriso = shutil.which("xorriso")
    if xorriso:
        return [xorriso, "-as", "mkisofs"]
    for name in ("genisoimage", "mkisofs"):
        tool = shutil.which(name)
        if tool:
            return [tool]
    return None


def extract_iso_member(iso_path: Path, member: str, dest: Path) -> bool:
    xorriso = shutil.which("xorriso")
    if not xorriso:
        return False
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        subprocess.check_call([xorriso, "-osirrox", "on", "-indev", str(iso_path), "-extract", member, str(dest)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return dest.exists() and dest.stat().st_size > 0
    except Exception:
        return False


def prepare_ubuntu_iso_autoinstall_kernel(base: Path, vm_dir: Path) -> Optional[Tuple[Path, Path]]:
    boot_dir = vm_dir / "ubuntu-autoinstall-boot"
    kernel = boot_dir / "vmlinuz"
    initrd = boot_dir / "initrd"
    if kernel.exists() and initrd.exists():
        return kernel, initrd
    if extract_iso_member(base, "/casper/vmlinuz", kernel) and extract_iso_member(base, "/casper/initrd", initrd):
        return kernel, initrd
    return None


def create_linux_unattended_seed_iso(
    vm_dir: Path, img: ImageItem,
    username: str, password: str, hostname: str,
    ssh_public_key: Optional[str] = None,
    iso_autoinstall: bool = True,
    linux_inject_repos: bool = False, linux_repo_profile: str = "global",
    linux_repo_update: bool = True, linux_repo_fix_dns: bool = True,
) -> Tuple[Path, str]:
    iso_builder = find_iso_builder()
    if not iso_builder:
        raise RuntimeError("Linux seed ISO needs genisoimage, mkisofs, or xorriso. Install: sudo apt-get install -y genisoimage xorriso")
    seed_dir = vm_dir / "linux-seed"
    seed_dir.mkdir(parents=True, exist_ok=True)
    mode = "cloud-init-seed"
    volume_label = "CIDATA"
    if img.distro == "ubuntu" and img.kind == "iso" and iso_autoinstall:
        user_data = build_ubuntu_autoinstall_user_data(username, password, hostname, ssh_public_key, linux_inject_repos, linux_repo_profile, linux_repo_update, linux_repo_fix_dns)
        mode = "ubuntu-autoinstall"
        (seed_dir / "user-data").write_text(user_data, encoding="utf-8")
        (seed_dir / "meta-data").write_text(f"instance-id: {uuid.uuid4()}\nlocal-hostname: {sanitize_hostname(hostname)}\n", encoding="utf-8")
    else:
        user_data = build_linux_cloud_init_user_data(username, password, hostname, ssh_public_key, linux_inject_repos, linux_repo_profile, linux_repo_update, linux_repo_fix_dns)
        (seed_dir / "user-data").write_text(user_data, encoding="utf-8")
        (seed_dir / "meta-data").write_text(f"instance-id: {uuid.uuid4()}\nlocal-hostname: {sanitize_hostname(hostname)}\n", encoding="utf-8")
    seed_iso = vm_dir / "linux-seed.iso"
    subprocess.check_call(iso_builder + ["-quiet", "-J", "-r", "-V", volume_label, "-o", str(seed_iso), str(seed_dir)])
    return seed_iso, mode


def create_overlay(base: Path, overlay: Path) -> None:
    if overlay.exists():
        return
    qemu_img = shutil.which("qemu-img")
    if not qemu_img:
        raise RuntimeError("qemu-img not found. Install qemu-utils.")
    fmt = qemu_img_format(base)
    subprocess.check_call([qemu_img, "create", "-f", "qcow2", "-F", fmt, "-b", str(base), str(overlay)])


def create_blank_disk(path: Path, size_gb: int) -> None:
    if path.exists():
        return
    qemu_img = shutil.which("qemu-img")
    if not qemu_img:
        raise RuntimeError("qemu-img not found. Install qemu-utils.")
    subprocess.check_call([qemu_img, "create", "-f", "qcow2", str(path), f"{size_gb}G"])


def windows_default_password() -> str:
    return "P@ssw0rd-" + secrets.token_hex(4)


def xml_escape(value: Any) -> str:
    return str(value).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def windows_domain_netbios(domain_name: str) -> str:
    first = (domain_name or "lab.local").split(".")[0]
    first = re.sub(r"[^A-Za-z0-9]", "", first).upper() or "LAB"
    return first[:15]


def build_windows_lab_config(
    admin_password: str, enable_rdp: bool = True, enable_winrm: bool = True,
    install_ad: bool = False, domain_name: str = "lab.local", dsrm_password: Optional[str] = None,
    install_iis: bool = False, install_dhcp: bool = False, install_file_server: bool = False,
    install_dotnet: bool = True, sharepoint_prereqs: bool = False,
    sharepoint_run_prereqinstaller: bool = True, sharepoint_run_setup: bool = False,
    sharepoint_product_key: Optional[str] = None, sharepoint_ca_port: int = 20199,
) -> Dict[str, Any]:
    domain_name = (domain_name or "lab.local").strip().lower()
    return {
        "enable_rdp": bool(enable_rdp), "enable_winrm": bool(enable_winrm),
        "install_ad": bool(install_ad), "domain_name": domain_name,
        "domain_netbios": windows_domain_netbios(domain_name),
        "dsrm_password": dsrm_password or admin_password,
        "install_iis": bool(install_iis), "install_dhcp": bool(install_dhcp),
        "install_file_server": bool(install_file_server), "install_dotnet": bool(install_dotnet),
        "sharepoint_prereqs": bool(sharepoint_prereqs),
        "sharepoint_run_prereqinstaller": bool(sharepoint_run_prereqinstaller),
        "sharepoint_run_setup": bool(sharepoint_run_setup),
        "sharepoint_product_key": sharepoint_product_key or "",
        "sharepoint_ca_port": int(sharepoint_ca_port or 20199),
    }


def build_windows_autounattend_xml(admin_password: str, image_index: int, computer_name: str, run_postinstall: bool = True) -> str:
    image_index = int(image_index or 2)
    admin_password_xml = xml_escape(admin_password)
    computer_name = xml_escape((computer_name or "KVM-WIN")[:15])
    postinstall_xml = ""
    if run_postinstall:
        cmd = "cmd.exe /c for %D in (D E F G H I J K L M N O P Q R S T U V W X Y Z) do if exist %D:\\postinstall.cmd call %D:\\postinstall.cmd"
        postinstall_xml = f"""
      <AutoLogon>
        <Password><Value>{admin_password_xml}</Value><PlainText>true</PlainText></Password>
        <Enabled>true</Enabled><LogonCount>1</LogonCount><Username>Administrator</Username>
      </AutoLogon>
      <FirstLogonCommands>
        <SynchronousCommand wcm:action="add">
          <Order>1</Order>
          <Description>KVM-P2P Windows lab post-install automation</Description>
          <CommandLine>{xml_escape(cmd)}</CommandLine>
          <RequiresUserInput>false</RequiresUserInput>
        </SynchronousCommand>
      </FirstLogonCommands>"""
    return f"""<?xml version="1.0" encoding="utf-8"?>
<unattend xmlns="urn:schemas-microsoft-com:unattend"
          xmlns:wcm="http://schemas.microsoft.com/WMIConfig/2002/State"
          xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <settings pass="windowsPE">
    <component name="Microsoft-Windows-International-Core-WinPE" processorArchitecture="amd64" publicKeyToken="31bf3856ad364e35" language="neutral" versionScope="nonSxS">
      <SetupUILanguage><UILanguage>en-US</UILanguage></SetupUILanguage>
      <InputLocale>en-US</InputLocale><SystemLocale>en-US</SystemLocale>
      <UILanguage>en-US</UILanguage><UserLocale>en-US</UserLocale>
    </component>
    <component name="Microsoft-Windows-Setup" processorArchitecture="amd64" publicKeyToken="31bf3856ad364e35" language="neutral" versionScope="nonSxS">
      <DiskConfiguration>
        <Disk wcm:action="add">
          <DiskID>0</DiskID><WillWipeDisk>true</WillWipeDisk>
          <CreatePartitions>
            <CreatePartition wcm:action="add"><Order>1</Order><Type>Primary</Type><Size>500</Size></CreatePartition>
            <CreatePartition wcm:action="add"><Order>2</Order><Type>Primary</Type><Extend>true</Extend></CreatePartition>
          </CreatePartitions>
          <ModifyPartitions>
            <ModifyPartition wcm:action="add"><Order>1</Order><PartitionID>1</PartitionID><Label>System</Label><Format>NTFS</Format><Active>true</Active></ModifyPartition>
            <ModifyPartition wcm:action="add"><Order>2</Order><PartitionID>2</PartitionID><Label>Windows</Label><Letter>C</Letter><Format>NTFS</Format></ModifyPartition>
          </ModifyPartitions>
        </Disk>
        <WillShowUI>OnError</WillShowUI>
      </DiskConfiguration>
      <ImageInstall>
        <OSImage>
          <InstallFrom><MetaData wcm:action="add"><Key>/IMAGE/INDEX</Key><Value>{image_index}</Value></MetaData></InstallFrom>
          <InstallTo><DiskID>0</DiskID><PartitionID>2</PartitionID></InstallTo>
          <WillShowUI>OnError</WillShowUI>
        </OSImage>
      </ImageInstall>
      <UserData><AcceptEula>true</AcceptEula><FullName>qemu</FullName><Organization>kvm-p2p</Organization></UserData>
    </component>
  </settings>
  <settings pass="specialize">
    <component name="Microsoft-Windows-Shell-Setup" processorArchitecture="amd64" publicKeyToken="31bf3856ad364e35" language="neutral" versionScope="nonSxS">
      <ComputerName>{computer_name}</ComputerName><TimeZone>UTC</TimeZone>
    </component>
  </settings>
  <settings pass="oobeSystem">
    <component name="Microsoft-Windows-Shell-Setup" processorArchitecture="amd64" publicKeyToken="31bf3856ad364e35" language="neutral" versionScope="nonSxS">
      <OOBE>
        <HideEULAPage>true</HideEULAPage><HideLocalAccountScreen>true</HideLocalAccountScreen>
        <HideOEMRegistrationScreen>true</HideOEMRegistrationScreen>
        <HideOnlineAccountScreens>true</HideOnlineAccountScreens>
        <HideWirelessSetupInOOBE>true</HideWirelessSetupInOOBE>
        <NetworkLocation>Work</NetworkLocation><ProtectYourPC>3</ProtectYourPC>
      </OOBE>
      <UserAccounts><AdministratorPassword><Value>{admin_password_xml}</Value><PlainText>true</PlainText></AdministratorPassword></UserAccounts>{postinstall_xml}
    </component>
  </settings>
</unattend>
"""


def build_windows_postinstall_cmd() -> str:
    return r"""@echo off
setlocal
mkdir C:\KVM-P2P 2>nul
xcopy /E /Y "%~d0\*" C:\KVM-P2P\ > C:\KVM-P2P\payload-copy.log 2>&1
powershell.exe -NoProfile -ExecutionPolicy Bypass -File C:\KVM-P2P\postinstall.ps1
exit /b 0
"""


def build_windows_postinstall_ps1() -> str:
    return r"""$ErrorActionPreference = "Continue"
$Base = "C:\KVM-P2P"
$Log = Join-Path $Base "postinstall.log"
$StatePath = Join-Path $Base "postinstall-state.json"
$ConfigPath = Join-Path $Base "lab-config.json"
New-Item -ItemType Directory -Force -Path $Base | Out-Null
function Write-Log([string]$Message) {
    "{0} {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Message | Tee-Object -FilePath $Log -Append
}
function Get-Stage {
    if (Test-Path $StatePath) { try { return [int]((Get-Content $StatePath -Raw | ConvertFrom-Json).stage) } catch { return 0 } }
    return 0
}
function Set-Stage([int]$Stage) {
    @{stage=$Stage; updated=(Get-Date).ToString("o")} | ConvertTo-Json | Set-Content -Encoding UTF8 $StatePath
}
function Ensure-PostInstallTask {
    try {
        $action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$Base\postinstall.ps1`""
        $trigger = New-ScheduledTaskTrigger -AtStartup
        Register-ScheduledTask -TaskName "KvmP2PPostInstall" -Action $action -Trigger $trigger -User "SYSTEM" -RunLevel Highest -Force | Out-Null
    } catch { Write-Log "Could not register scheduled task: $($_.Exception.Message)" }
}
function Remove-PostInstallTask { try { Unregister-ScheduledTask -TaskName "KvmP2PPostInstall" -Confirm:$false -ErrorAction SilentlyContinue } catch {} }
function Enable-Rdp {
    try { Set-ItemProperty -Path "HKLM:\System\CurrentControlSet\Control\Terminal Server" -Name "fDenyTSConnections" -Value 0 } catch {}
    try { Enable-NetFirewallRule -DisplayGroup "Remote Desktop" -ErrorAction SilentlyContinue | Out-Null } catch {}
}
function Enable-WinRm {
    try { Enable-PSRemoting -Force -SkipNetworkProfileCheck | Out-Null } catch { Write-Log "Enable-PSRemoting: $($_.Exception.Message)" }
    try { winrm quickconfig -quiet | Out-Null } catch {}
    try { Enable-NetFirewallRule -Name "WINRM-HTTP-In-TCP" -ErrorAction SilentlyContinue | Out-Null } catch {}
}
Write-Log "Starting KVM-P2P Windows post-install automation."
if (!(Test-Path $ConfigPath)) { Write-Log "No lab-config.json found; nothing to do."; exit 0 }
$config = Get-Content $ConfigPath -Raw | ConvertFrom-Json
Ensure-PostInstallTask
$stage = Get-Stage
Write-Log "Current stage: $stage"
try {
    if ($stage -lt 1) {
        if ($config.enable_rdp) { Enable-Rdp; Write-Log "RDP enabled." }
        if ($config.enable_winrm) { Enable-WinRm; Write-Log "WinRM enabled." }
        $features = New-Object 'System.Collections.Generic.List[string]'
        if ($config.install_dotnet) { foreach ($f in @('NET-Framework-45-Features','NET-Framework-45-Core','NET-WCF-Services45','NET-WCF-TCP-PortSharing45')) { [void]$features.Add($f) } }
        if ($config.install_iis) { foreach ($f in @('Web-Server','Web-WebServer','Web-Common-Http','Web-Default-Doc','Web-Static-Content','Web-Http-Errors','Web-Health','Web-Http-Logging','Web-Performance','Web-Stat-Compression','Web-Security','Web-Filtering','Web-App-Dev','Web-Net-Ext45','Web-Asp-Net45','Web-ISAPI-Ext','Web-ISAPI-Filter','Web-Mgmt-Tools','Web-Mgmt-Console')) { [void]$features.Add($f) } }
        if ($config.install_file_server) { foreach ($f in @('File-Services','FS-FileServer')) { [void]$features.Add($f) } }
        if ($config.install_dhcp) { foreach ($f in @('DHCP','RSAT-DHCP')) { [void]$features.Add($f) } }
        if ($config.install_ad) { foreach ($f in @('AD-Domain-Services','DNS','RSAT-AD-Tools')) { [void]$features.Add($f) } }
        if ($features.Count -gt 0) {
            Write-Log "Installing Windows features: $($features -join ', ')"
            try { Install-WindowsFeature -Name $features.ToArray() -IncludeManagementTools -ErrorAction Continue | Out-String | Tee-Object -FilePath $Log -Append } catch { Write-Log "Install-WindowsFeature error: $($_.Exception.Message)" }
        }
        if ($config.install_ad) {
            Write-Log "Promoting to AD DS forest: $($config.domain_name)"
            Set-Stage 1
            try {
                Import-Module ADDSDeployment -ErrorAction Stop
                $secure = ConvertTo-SecureString ([string]$config.dsrm_password) -AsPlainText -Force
                Install-ADDSForest -DomainName ([string]$config.domain_name) -DomainNetbiosName ([string]$config.domain_netbios) -SafeModeAdministratorPassword $secure -InstallDns:$true -NoRebootOnCompletion:$false -Force
                exit 0
            } catch { Write-Log "AD DS promotion failed: $($_.Exception.Message)" }
        }
        Set-Stage 1; $stage = 1
    }
    Set-Stage 99
    Remove-PostInstallTask
    Write-Log "KVM-P2P Windows post-install automation finished."
} catch { Write-Log "Fatal post-install error: $($_.Exception.Message)"; throw }
"""


def create_windows_autounattend_iso(vm_dir: Path, admin_password: str, image_index: int, lab_config: Optional[Dict[str, Any]] = None) -> Path:
    iso_builder = find_iso_builder()
    if not iso_builder:
        raise RuntimeError("Windows unattended install needs genisoimage, mkisofs, or xorriso.")
    seed_dir = vm_dir / "autounattend"
    seed_dir.mkdir(parents=True, exist_ok=True)
    computer_name = ("KVM" + uuid.uuid4().hex[:8]).upper()
    (seed_dir / "Autounattend.xml").write_text(build_windows_autounattend_xml(admin_password, image_index, computer_name, run_postinstall=lab_config is not None), encoding="utf-8")
    if lab_config is not None:
        (seed_dir / "lab-config.json").write_text(json.dumps(lab_config, indent=2), encoding="utf-8")
        (seed_dir / "postinstall.cmd").write_text(build_windows_postinstall_cmd(), encoding="utf-8")
        (seed_dir / "postinstall.ps1").write_text(build_windows_postinstall_ps1(), encoding="utf-8")
    answer_iso = vm_dir / "autounattend.iso"
    subprocess.check_call(iso_builder + ["-quiet", "-J", "-r", "-V", "AUTOUNATTEND", "-o", str(answer_iso), str(seed_dir)])
    return answer_iso


def looks_like_iso9660(path: Path) -> bool:
    try:
        with path.open("rb") as f:
            f.seek(16 * 2048)
            data = f.read(4096)
        return b"CD001" in data
    except Exception:
        return False


def validate_boot_image_before_launch(img: ImageItem, path: Path) -> None:
    if img.kind != "iso":
        return
    if not path.exists():
        raise RuntimeError(f"image is missing: {path}")
    size = path.stat().st_size
    if img.family == "windows":
        if size < 1024 * 1024 * 1024:
            raise RuntimeError(
                f"Windows ISO looks too small ({size} bytes): {path}. "
                "Likely an HTML error page or incomplete download. Delete and redownload."
            )
        if not looks_like_iso9660(path):
            raise RuntimeError(f"Windows ISO does not look like valid ISO9660/UDF: {path}.")


def spawn_qemu(
    image_id: str, cpus: int, ram_mb: int, disk_gb: int,
    job_id: Optional[str] = None,
    windows_unattended: bool = True, windows_admin_password: Optional[str] = None,
    windows_image_index: int = 2, windows_enable_rdp: bool = True,
    windows_enable_winrm: bool = True, windows_role_ad: bool = False,
    windows_domain_name: str = "lab.local", windows_dsrm_password: Optional[str] = None,
    windows_role_iis: bool = False, windows_role_dhcp: bool = False,
    windows_role_fileserver: bool = False, windows_role_dotnet: bool = True,
    windows_sharepoint_prereqs: bool = False, windows_sharepoint_iso_path: Optional[str] = None,
    windows_sharepoint_run_prereqinstaller: bool = True, windows_sharepoint_run_setup: bool = False,
    windows_sharepoint_product_key: Optional[str] = None, windows_sharepoint_ca_port: int = 20199,
    linux_unattended: bool = True, linux_username: str = "qemu",
    linux_password: Optional[str] = None, linux_hostname: Optional[str] = None,
    linux_ssh_public_key: Optional[str] = None, linux_iso_autoinstall: bool = True,
    linux_inject_repos: bool = True, linux_repo_profile: str = "global",
    linux_repo_update: bool = True, linux_repo_fix_dns: bool = True,
) -> Dict[str, Any]:
    _dirs()
    img = CAT_BY_ID[image_id]
    base = local_image_path(img)
    if not base.exists():
        raise RuntimeError(f"image not downloaded: {image_id}")
    validate_boot_image_before_launch(img, base)
    qemu = shutil.which("qemu-system-x86_64")
    if not qemu:
        raise RuntimeError("qemu-system-x86_64 not found. Install qemu-system-x86.")
    vm_id = f"{image_id}-{uuid.uuid4().hex[:8]}"
    vm_dir = VMS_DIR / vm_id
    vm_dir.mkdir(parents=True, exist_ok=True)
    ssh_port   = find_free_port(2200, 8999)
    http_port  = find_free_port(18080, 25000)
    vnc_port   = find_free_port(5901, 5999)
    ws_port    = find_free_port(5700, 5799)
    rdp_port   = find_free_port(3389, 3499) if img.family == "windows" else None
    winrm_port = find_free_port(5985, 6099) if img.family == "windows" else None
    https_port = find_free_port(18443, 18999) if img.family == "windows" else None
    sp_ca_host_port = find_free_port(20000, 21999) if img.family == "windows" and windows_sharepoint_prereqs else None
    log_path = LOGS_DIR / f"qemu-{vm_id}.log"
    hostfwds = f"hostfwd=tcp:127.0.0.1:{ssh_port}-:22,hostfwd=tcp:127.0.0.1:{http_port}-:80"
    if rdp_port:   hostfwds += f",hostfwd=tcp:127.0.0.1:{rdp_port}-:3389"
    if winrm_port: hostfwds += f",hostfwd=tcp:127.0.0.1:{winrm_port}-:5985"
    if https_port: hostfwds += f",hostfwd=tcp:127.0.0.1:{https_port}-:443"
    if sp_ca_host_port: hostfwds += f",hostfwd=tcp:127.0.0.1:{sp_ca_host_port}-:{int(windows_sharepoint_ca_port or 20199)}"
    use_kvm = Path("/dev/kvm").exists() and os.access("/dev/kvm", os.R_OK | os.W_OK)
    vnc_display = vnc_port - 5900
    cmd = [qemu]
    if use_kvm:
        cmd += ["-enable-kvm"]
    else:
        cmd += ["-accel", "tcg"]
    cmd += [
        "-machine", "q35",
        "-cpu", "host" if use_kvm else "max",
        "-smp", str(max(1, int(cpus))),
        "-m", str(max(512, int(ram_mb))),
        "-display", "none",
        "-vga", "std",
    ]
    if qemu_supports_audiodev_none(qemu):
        cmd += ["-audiodev", "none,id=noaudio"]
    cmd += [
        "-vnc", f"{BIND_HOST}:{vnc_display},websocket={ws_port}",
        "-netdev", f"user,id=n0,{hostfwds}",
        "-device", "e1000,netdev=n0" if img.family == "windows" else "virtio-net-pci,netdev=n0",
    ]
    linux_info: Optional[Dict[str, Any]] = None
    windows_info: Optional[Dict[str, Any]] = None
    if img.kind == "cloud":
        overlay = vm_dir / "disk.qcow2"
        create_overlay(base, overlay)
        cmd += ["-drive", f"file={overlay},if=virtio,format=qcow2"]
        if img.family == "linux":
            linux_username  = sanitize_linux_username(linux_username)
            linux_password  = linux_password or linux_default_password()
            linux_hostname_final = sanitize_hostname(linux_hostname, fallback=vm_id)
            seed = create_cloud_init_seed(vm_dir, linux_username, linux_password, linux_hostname_final, linux_ssh_public_key, linux_inject_repos, linux_repo_profile, linux_repo_update, linux_repo_fix_dns)
            linux_info = {"unattended": True, "mode": "cloud-init", "user": linux_username, "password": linux_password, "hostname": linux_hostname_final, "seed_iso": str(seed) if seed else None, "ssh_hint": f"ssh -p {ssh_port} {linux_username}@127.0.0.1"}
        else:
            seed = create_cloud_init_seed(vm_dir)
        if seed:
            cmd += ["-drive", f"file={seed},media=cdrom,readonly=on"]
        cmd += ["-boot", "c"]
    else:
        disk = vm_dir / "disk.qcow2"
        create_blank_disk(disk, disk_gb)
        if img.family == "windows":
            windows_admin_password = windows_admin_password or windows_default_password()
            lab_config = build_windows_lab_config(
                admin_password=windows_admin_password, enable_rdp=windows_enable_rdp,
                enable_winrm=windows_enable_winrm, install_ad=windows_role_ad,
                domain_name=windows_domain_name, dsrm_password=windows_dsrm_password,
                install_iis=windows_role_iis, install_dhcp=windows_role_dhcp,
                install_file_server=windows_role_fileserver, install_dotnet=windows_role_dotnet,
                sharepoint_prereqs=windows_sharepoint_prereqs,
                sharepoint_run_prereqinstaller=windows_sharepoint_run_prereqinstaller,
                sharepoint_run_setup=windows_sharepoint_run_setup,
                sharepoint_product_key=windows_sharepoint_product_key,
                sharepoint_ca_port=int(windows_sharepoint_ca_port or 20199),
            )
            answer_iso = create_windows_autounattend_iso(vm_dir, windows_admin_password, int(windows_image_index or 2), lab_config=lab_config) if windows_unattended else None
            cmd += [
                "-device", "ich9-ahci,id=sata",
                "-drive", f"file={disk},if=none,id=win_disk,format=qcow2",
                "-device", "ide-hd,drive=win_disk,bus=sata.0",
                "-drive", f"file={base},if=none,id=win_iso,media=cdrom,readonly=on",
                "-device", "ide-cd,drive=win_iso,bus=sata.1",
            ]
            if answer_iso:
                cmd += ["-drive", f"file={answer_iso},if=none,id=answer_iso,media=cdrom,readonly=on", "-device", "ide-cd,drive=answer_iso,bus=sata.2"]
            virtio = IMAGES_DIR / "virtio-win.iso"
            if virtio.exists():
                cmd += ["-drive", f"file={virtio},if=none,id=virtio_iso,media=cdrom,readonly=on", "-device", "ide-cd,drive=virtio_iso,bus=sata.3"]
            sp_iso_path = Path(windows_sharepoint_iso_path).expanduser() if windows_sharepoint_iso_path else None
            if sp_iso_path and sp_iso_path.exists():
                cmd += ["-drive", f"file={sp_iso_path},if=none,id=sharepoint_iso,media=cdrom,readonly=on", "-device", "ide-cd,drive=sharepoint_iso,bus=sata.4"]
            elif windows_sharepoint_iso_path:
                print(f"[warn] sharepoint ISO not found: {windows_sharepoint_iso_path}", file=sys.stderr)
            cmd += ["-boot", "order=c,once=d,menu=on"]
            windows_info = {"unattended": bool(windows_unattended), "admin_user": "Administrator", "admin_password": windows_admin_password if windows_unattended else None, "image_index": int(windows_image_index or 2), "autounattend_iso": str(answer_iso) if answer_iso else None, "roles": lab_config}
        else:
            if img.family == "linux" and linux_unattended:
                linux_username = sanitize_linux_username(linux_username)
                linux_password = linux_password or linux_default_password()
                linux_hostname_final = sanitize_hostname(linux_hostname, fallback=vm_id)
                linux_seed, linux_seed_mode = create_linux_unattended_seed_iso(vm_dir, img, linux_username, linux_password, linux_hostname_final, linux_ssh_public_key, linux_iso_autoinstall, linux_inject_repos, linux_repo_profile, linux_repo_update, linux_repo_fix_dns)
                cmd += ["-drive", f"file={disk},if=virtio,format=qcow2", "-drive", f"file={base},media=cdrom,readonly=on", "-drive", f"file={linux_seed},media=cdrom,readonly=on"]
                if img.distro == "ubuntu" and linux_iso_autoinstall and "live-server" in base.name:
                    pair = prepare_ubuntu_iso_autoinstall_kernel(base, vm_dir)
                    if pair:
                        kernel, initrd = pair
                        cmd += ["-kernel", str(kernel), "-initrd", str(initrd), "-append", "autoinstall ds=nocloud ---"]
                    else:
                        cmd += ["-boot", "d"]
                else:
                    cmd += ["-boot", "d"]
                linux_info = {"unattended": True, "mode": linux_seed_mode, "user": linux_username, "password": linux_password, "hostname": linux_hostname_final, "seed_iso": str(linux_seed), "ssh_hint": f"ssh -p {ssh_port} {linux_username}@127.0.0.1"}
            else:
                cmd += ["-drive", f"file={disk},if=virtio,format=qcow2", "-drive", f"file={base},media=cdrom,readonly=on", "-boot", "d"]
    (LOGS_DIR / f"cmd-{vm_id}.txt").write_text(" ".join(cmd) + "\n", encoding="utf-8")
    with log_path.open("ab") as log:
        proc = subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT, start_new_session=True, env=qemu_child_env())
    VM_PROCS[vm_id] = proc
    rec: Dict[str, Any] = {
        "id": vm_id, "image_id": image_id, "name": img.name, "pid": proc.pid,
        "vnc": f"127.0.0.1:{vnc_port}", "vnc_port": vnc_port, "ws_port": ws_port,
        "console_proxy": f"/api/vms/{vm_id}/console",
        "ssh": f"ssh -p {ssh_port} qemu@127.0.0.1", "ssh_port": ssh_port,
        "http": f"http://127.0.0.1:{http_port}/", "http_port": http_port,
        "rdp": f"mstsc /v:127.0.0.1:{rdp_port}" if rdp_port else None, "rdp_port": rdp_port,
        "winrm": f"http://127.0.0.1:{winrm_port}/wsman" if winrm_port else None, "winrm_port": winrm_port,
        "https": f"https://127.0.0.1:{https_port}/" if https_port else None, "https_port": https_port,
        "sharepoint_central_admin_port": sp_ca_host_port,
        "log": str(log_path), "vm_dir": str(vm_dir), "created_at": now(), "running": True,
    }
    if windows_info: rec["windows"] = windows_info
    if linux_info:   rec["linux"]   = linux_info
    RUNNING_VMS[vm_id] = rec
    return rec


async def provision_vm(image_id: str, cpus: int, ram_mb: int, disk_gb: int, job_id: str, **kwargs: Any) -> None:
    PROVISION[job_id].update({"phase": "download", "message": "ensuring image is downloaded"})
    try:
        await ensure_download(image_id)
        PROVISION[job_id].update({"phase": "boot", "message": "starting qemu"})
        rec = spawn_qemu(image_id, cpus, ram_mb, disk_gb, job_id=job_id, **kwargs)
        PROVISION[job_id].update({"phase": "done", "message": "vm started", "vm": rec})
    except Exception as e:
        PROVISION[job_id].update({"phase": "error", "message": str(e)})


def vm_list() -> List[Dict[str, Any]]:
    out = []
    for vm_id, rec in list(RUNNING_VMS.items()):
        proc = VM_PROCS.get(vm_id)
        rec["running"] = bool(proc and proc.poll() is None)
        out.append(rec.copy())
    return out


def stop_vm(vm_id: str) -> bool:
    proc = VM_PROCS.get(vm_id)
    if not proc:
        return False
    if proc.poll() is None:
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        except Exception:
            proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            except Exception:
                proc.kill()
    RUNNING_VMS.get(vm_id, {})["running"] = False
    return True


def find_novnc_dir() -> Optional[Path]:
    candidates: List[Path] = []
    env_dir = os.environ.get("KVM_P2P_NOVNC_DIR") or os.environ.get("NOVNC_DIR")
    if env_dir:
        candidates.append(Path(env_dir).expanduser())
    candidates += [DATA_DIR / "novnc", Path("/usr/share/novnc"), Path("/usr/local/share/novnc"), Path("/opt/novnc")]
    for d in candidates:
        try:
            p = d.resolve()
            if (p / "core" / "rfb.js").exists():
                return p
        except Exception:
            continue
    return None


CLIENT_HTML = r"""<!doctype html>
<html>
<head>
  <meta charset="utf-8" /><title>KVM Auto Downloader</title>
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <style>
    body{font-family:system-ui,Arial,sans-serif;margin:0;background:#111827;color:#e5e7eb}
    header{padding:18px 24px;background:#0b1220;border-bottom:1px solid #374151}
    h1{margin:0 0 6px;font-size:22px}
    main{padding:18px 24px;max-width:1180px;margin:auto}
    button{background:#2563eb;color:white;border:0;border-radius:8px;padding:8px 12px;margin:4px;cursor:pointer}
    button.secondary{background:#374151} button.danger{background:#b91c1c}
    input,select{background:#1f2937;color:#e5e7eb;border:1px solid #4b5563;border-radius:8px;padding:8px;margin:4px}
    .grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:12px}
    .card{background:#1f2937;border:1px solid #374151;border-radius:12px;padding:14px}
    .form-box{background:#111827;border:1px solid #374151;border-radius:12px;padding:12px;margin:8px 0}
    .form-box h3{margin:0 0 8px;font-size:16px;color:#bfdbfe}
    .row{display:flex;flex-wrap:wrap;gap:8px 12px;align-items:center;margin:6px 0}
    .row label{display:inline-flex;align-items:center;gap:6px}
    .wide{width:min(100%,760px)}
    .hidden{display:none!important}
    .muted{color:#9ca3af;font-size:13px}
    .ok{color:#86efac} .warn{color:#fbbf24} .bad{color:#fca5a5}
    progress{width:100%;height:18px}
    pre{white-space:pre-wrap;background:#0b1220;padding:10px;border-radius:8px;overflow:auto}
    table{width:100%;border-collapse:collapse} td,th{border-bottom:1px solid #374151;padding:8px;text-align:left}
    #consoleModal{display:none;position:fixed;inset:0;background:rgba(0,0,0,.85);z-index:50;padding:16px}
    #consoleModal .wrap{max-width:1200px;margin:0 auto;height:100%;display:flex;flex-direction:column}
    #consoleModal .bar{display:flex;justify-content:space-between;align-items:center;gap:8px;margin-bottom:8px}
    #screen{flex:1;background:#000;border:1px solid #374151;border-radius:10px;overflow:hidden}
  </style>
</head>
<body>
<header>
  <h1>KVM Auto Downloader + QEMU</h1>
  <div class="muted">Download Linux/BSD/Windows images, verify checksums, boot with localhost ports and in-browser console.</div>
</header>
<main>
  <div>
    <button onclick="show('catalog')">Auto Downloader</button>
    <button onclick="show('downloads')">Downloads</button>
    <button onclick="show('launch')">Launch VM</button>
    <button onclick="show('vms')">Running VMs</button>
  </div>
  <section id="catalog">
    <h2>Catalog</h2>
    <select id="filter" onchange="renderCatalog()">
      <option value="all">all</option><option value="linux">linux</option>
      <option value="windows">windows</option><option value="bsd">bsd</option>
    </select>
    <input id="search" placeholder="search..." oninput="renderCatalog()" />
    <button onclick="downloadAll()">Download All (filter)</button>
    <div id="cards" class="grid"></div>
  </section>
  <section id="downloads" style="display:none"><h2>Downloads</h2><div id="downloadRows"></div></section>
  <section id="launch" style="display:none">
    <h2>Launch VM</h2>
    <div class="card">
      <div class="form-box">
        <h3>Basic</h3>
        <div class="row">
          <label>Image <select id="launchImage" onchange="updateLaunchUi()"></select></label>
          <label>CPU <input id="cpus" type="number" value="2" min="1" max="32" /></label>
          <label>RAM MB <input id="ram" type="number" value="4096" min="512" /></label>
          <label>Disk GB <input id="disk" type="number" value="60" min="20" /></label>
        </div>
        <div id="imageHint" class="muted"></div>
      </div>
      <div id="linuxOptions" class="form-box hidden">
        <h3>Linux options</h3>
        <div class="row">
          <label><input id="linuxUnattended" type="checkbox" checked /> unattended</label>
          <label><input id="linuxInjectRepos" type="checkbox" checked onchange="updateLaunchUi()" /> inject repos</label>
          <label>Profile <select id="linuxRepoProfile" onchange="updateLaunchUi()"><option value="global">Global</option><option value="israel">Israel</option><option value="none">None</option></select></label>
          <label><input id="linuxRepoUpdate" type="checkbox" checked /> update</label>
          <label><input id="linuxRepoFixDns" type="checkbox" checked /> fix DNS</label>
        </div>
        <div class="row">
          <label>User <input id="linuxUser" type="text" value="qemu" /></label>
          <label>Password <input id="linuxPassword" type="text" placeholder="auto" /></label>
          <label>Hostname <input id="linuxHostname" type="text" placeholder="auto" /></label>
        </div>
        <div class="row"><label class="wide">SSH key <input id="linuxSshKey" class="wide" type="text" placeholder="optional ssh-ed25519..." /></label></div>
      </div>
      <div id="windowsOptions" class="form-box hidden">
        <h3>Windows options</h3>
        <div class="row">
          <label><input id="winUnattended" type="checkbox" checked /> unattended</label>
          <label>Image index <input id="winIndex" type="number" value="2" min="1" max="20" /></label>
          <label>Admin password <input id="winPassword" type="text" placeholder="auto" /></label>
        </div>
        <div class="row">
          <label><input id="winRdp" type="checkbox" checked /> RDP</label>
          <label><input id="winWinrm" type="checkbox" checked /> WinRM</label>
          <label><input id="winDotnet" type="checkbox" checked /> .NET</label>
          <label><input id="winIis" type="checkbox" /> IIS</label>
          <label><input id="winDhcp" type="checkbox" /> DHCP</label>
          <label><input id="winFileServer" type="checkbox" /> File Server</label>
          <label><input id="winAd" type="checkbox" /> AD DS</label>
        </div>
        <div class="row"><label>Domain <input id="winDomain" type="text" value="lab.local" /></label><label>DSRM password <input id="winDsrm" type="text" placeholder="same as admin" /></label></div>
      </div>
      <div class="form-box"><button onclick="launchVm()">LAUNCH</button><pre id="launchStatus"></pre></div>
    </div>
  </section>
  <section id="vms" style="display:none"><h2>Running VMs</h2><div id="vmRows"></div></section>
</main>
<div id="consoleModal">
  <div class="wrap">
    <div class="bar">
      <b id="consoleTitle">QEMU Console</b>
      <span>
        <span id="consoleState" class="muted">connecting...</span>
        <button class="secondary" onclick="sendCAD()">Ctrl+Alt+Del</button>
        <button class="secondary" onclick="toggleFit()">Fit</button>
        <button class="danger" onclick="closeConsole()">Close</button>
      </span>
    </div>
    <div id="screen"></div>
  </div>
</div>
<script>
let catalog=[], currentTab='catalog', rfb=null, fit=true;
const $=id=>document.getElementById(id);
const val=(id,fb='')=>{const e=$(id);return e?e.value:fb;};
const checked=(id,fb=false)=>{const e=$(id);return e?!!e.checked:fb;};
const num=(id,fb)=>{const n=Number(val(id,fb));return Number.isFinite(n)?n:fb;};
function esc(s){return String(s||'').replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));}
async function loadCatalog(){
  const sel=$('launchImage'), prev=sel?sel.value:'';
  catalog=await(await fetch('/api/catalog',{cache:'no-store'})).json();
  renderCatalog();
  if(sel){
    sel.innerHTML=catalog.filter(x=>x.launchable).map(x=>`<option value="${x.id}">${esc(x.name)}${x.downloaded?' (ready)':x.needs_browser?' (manual)':''}</option>`).join('');
    if(prev&&catalog.some(x=>x.id===prev))sel.value=prev;
  }
  updateLaunchUi();
}
function show(id){
  currentTab=id;
  document.querySelectorAll('section').forEach(s=>s.style.display='none');
  const t=$(id);if(t)t.style.display='';
  tick();
}
function renderCatalog(){
  const f=$('filter').value, q=$('search').value.toLowerCase();
  const list=catalog.filter(x=>(f==='all'||x.family===f)&&JSON.stringify(x).toLowerCase().includes(q));
  $('cards').innerHTML=list.map(x=>`<div class="card"><b>${esc(x.name)}</b><br/><span class="muted">${esc(x.id)} | ${esc(x.family)} | ${esc(x.kind)}</span><br/><span class="${x.downloaded?'ok':x.needs_browser?'warn':'muted'}">${x.downloaded?'ready':x.needs_browser?'manual':'not downloaded'}</span><p class="muted">${esc(x.notes)}</p>${x.needs_browser?`<button onclick="openManual('${x.id}')">Open page</button>`:`<button onclick="downloadOne('${x.id}')">Download</button>`}</div>`).join('');
}
function updateLaunchUi(){
  const img=catalog.find(x=>x.id===val('launchImage',''))||null;
  const family=img?img.family:'';
  $('linuxOptions').classList.toggle('hidden',family!=='linux');
  $('windowsOptions').classList.toggle('hidden',family!=='windows');
  const inj=checked('linuxInjectRepos',true)&&val('linuxRepoProfile','global')!=='none';
  for(const id of['linuxRepoProfile','linuxRepoUpdate','linuxRepoFixDns']){const e=$(id);if(e)e.disabled=!checked('linuxInjectRepos',true);}
  const hint=$('imageHint');
  if(hint&&img)hint.textContent=`${img.name} | ${img.family}/${img.distro}/${img.kind} | ${img.downloaded?'ready':img.needs_browser?'manual download':' will auto-download'}`;
}
async function downloadOne(id){await fetch('/api/download/'+encodeURIComponent(id),{method:'POST'});show('downloads');}
async function openManual(id){const r=await fetch('/api/download/'+encodeURIComponent(id),{method:'POST'});const j=await r.json();if(j.browser_url)window.open(j.browser_url,'_blank');}
async function downloadAll(){await fetch('/api/download-all/'+$('filter').value,{method:'POST'});show('downloads');}
async function launchVm(){
  $('launchStatus').textContent='creating VM...';
  const body={
    image_id:val('launchImage'),cpus:num('cpus',2),ram_mb:num('ram',4096),disk_gb:num('disk',60),
    linux_unattended:checked('linuxUnattended',true),linux_username:val('linuxUser','qemu')||'qemu',
    linux_password:val('linuxPassword','')||null,linux_hostname:val('linuxHostname','')||null,
    linux_ssh_public_key:val('linuxSshKey','')||null,linux_iso_autoinstall:true,
    linux_inject_repos:checked('linuxInjectRepos',true)&&val('linuxRepoProfile','global')!=='none',
    linux_repo_profile:val('linuxRepoProfile','global')||'global',
    linux_repo_update:checked('linuxRepoUpdate',true),linux_repo_fix_dns:checked('linuxRepoFixDns',true),
    windows_unattended:checked('winUnattended',true),windows_image_index:num('winIndex',2)||2,
    windows_admin_password:val('winPassword','')||null,windows_enable_rdp:checked('winRdp',true),
    windows_enable_winrm:checked('winWinrm',true),windows_role_ad:checked('winAd',false),
    windows_domain_name:val('winDomain','lab.local')||'lab.local',windows_dsrm_password:val('winDsrm','')||null,
    windows_role_iis:checked('winIis',false),windows_role_dhcp:checked('winDhcp',false),
    windows_role_fileserver:checked('winFileServer',false),windows_role_dotnet:checked('winDotnet',true),
  };
  try{
    const res=await fetch('/api/vms/create',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
    const j=await res.json();
    $('launchStatus').textContent=JSON.stringify(j,null,2);
    if(res.ok&&j.job_id)pollProvision(j.job_id);
  }catch(e){$('launchStatus').textContent='Launch failed: '+e.message;}
}
async function pollProvision(job){
  const j=await(await fetch('/api/vms/provision/'+encodeURIComponent(job))).json();
  $('launchStatus').textContent=JSON.stringify(j,null,2);
  if(j.phase==='done'&&j.vm){renderVMs();return;}
  if(!['done','error'].includes(j.phase))setTimeout(()=>pollProvision(job),1500);
}
async function renderDownloads(){
  const d=await(await fetch('/api/downloads')).json();
  $('downloadRows').innerHTML=Object.values(d).map(x=>`<div class="card"><b>${esc(x.id)}</b> <span class="muted">${esc(x.phase)} ${esc(x.engine||'')}</span><progress max="100" value="${Number(x.progress||0)}"></progress><div>${Number(x.progress||0).toFixed(1)}% ${x.checksum_verified?'<span class="ok">✓ checksum</span>':''}</div><div class="muted">${esc(x.message)}</div></div>`).join('')||'<p class="muted">No downloads.</p>';
}
async function renderVMs(){
  const v=await(await fetch('/api/vms',{cache:'no-store'})).json();
  $('vmRows').innerHTML=`<table><tr><th>ID</th><th>Image</th><th>Console</th><th>SSH</th><th>State</th><th></th></tr>${(Array.isArray(v)?v:[]).map(x=>`<tr><td>${esc(x.id)}</td><td>${esc(x.image_id)}</td><td><button onclick="openConsole('${esc(x.id)}','${esc(x.id)}')">console</button></td><td><code>${esc(x.ssh)}</code></td><td>${x.running?'<span class="ok">running</span>':'<span class="bad">stopped</span>'}</td><td><button class="danger" onclick="stopVm('${esc(x.id)}')">stop</button></td></tr>`).join('')}</table>`;
}
async function stopVm(id){await fetch('/api/vms/'+encodeURIComponent(id)+'/stop',{method:'POST'});renderVMs();}
async function openConsole(vmId,title){
  const modal=$('consoleModal'),screen=$('screen');
  $('consoleTitle').textContent='QEMU Console - '+title;
  $('consoleState').textContent='connecting...';
  screen.innerHTML='';modal.style.display='block';
  let RFB;
  try{({default:RFB}=await import('/novnc/core/rfb.js'));}
  catch(e){
    let hint='noVNC missing. Install: sudo apt-get install -y novnc';
    try{const st=await(await fetch('/api/novnc-status')).json();if(st&&st.message)hint=st.message;}catch(_){}
    $('consoleState').textContent=hint;return;
  }
  const url=`${location.protocol==='https:'?'wss':'ws'}://${location.host}/api/vms/${encodeURIComponent(vmId)}/console`;
  try{
    rfb=new RFB(screen,url,{});rfb.scaleViewport=fit;
    rfb.addEventListener('connect',()=>{$('consoleState').textContent='connected';});
    rfb.addEventListener('disconnect',ev=>{$('consoleState').textContent='disconnected'+(ev.detail&&ev.detail.clean?'':' (QEMU stopped)');});
  }catch(e){$('consoleState').textContent='error: '+e.message;}
}
function closeConsole(){try{if(rfb){rfb.disconnect();rfb=null;}}catch(e){}$('consoleModal').style.display='none';$('screen').innerHTML='';}
function sendCAD(){try{if(rfb)rfb.sendCtrlAltDel();}catch(e){}}
function toggleFit(){fit=!fit;if(rfb)rfb.scaleViewport=fit;}
document.addEventListener('keydown',e=>{if(e.key==='Escape'&&$('consoleModal').style.display==='block')closeConsole();});
async function tick(){
  if(currentTab==='downloads')renderDownloads();
  else if(currentTab==='vms')renderVMs();
  else if(currentTab==='catalog')loadCatalog();
}
setInterval(tick,2000);
loadCatalog();
</script>
</body>
</html>"""


def build_app():
    try:
        from fastapi import BackgroundTasks, Body, FastAPI, HTTPException
        from fastapi import WebSocket as _WS  # noqa: F401
        from fastapi.responses import HTMLResponse, RedirectResponse
        from fastapi.staticfiles import StaticFiles
    except Exception as e:  # pragma: no cover
        raise RuntimeError("Install: pip install fastapi uvicorn aiohttp") from e

    app = FastAPI(title="KVM Auto Downloader + QEMU", version="2.0.0")

    novnc_dir = find_novnc_dir()
    if novnc_dir:
        app.mount("/novnc", StaticFiles(directory=str(novnc_dir)), name="novnc")

    @app.get("/", include_in_schema=False)
    async def root():
        return RedirectResponse("/client")

    @app.get("/client", response_class=HTMLResponse, include_in_schema=False)
    async def client():
        return CLIENT_HTML

    @app.get("/api/catalog")
    async def api_catalog():
        _dirs()
        return [img.public() for img in CATALOG]

    @app.get("/api/novnc-status")
    async def api_novnc_status():
        d = find_novnc_dir()
        if d:
            return {"available": True, "path": str(d), "message": f"noVNC from {d}"}
        return {"available": False, "path": None, "message": "noVNC missing. Install: sudo apt-get install -y novnc"}

    # WebSocket VNC proxy. The annotation is spelled out explicitly here so
    # FastAPI resolves it correctly even with `from __future__ import annotations`
    # active at module level (PEP 563 turns all annotations into strings, so
    # FastAPI's get_type_hints() looks up "WebSocket" in module globals where
    # it is always defined — either as fastapi.WebSocket or Any).
    @app.websocket("/api/vms/{vm_id}/console")
    async def api_vm_console(websocket: WebSocket, vm_id: str):
        proto_header = websocket.headers.get("sec-websocket-protocol", "") or ""
        subprotocol = "binary" if "binary" in proto_header.lower() else None
        await websocket.accept(subprotocol=subprotocol)
        rec = RUNNING_VMS.get(vm_id)
        console_log_path = LOGS_DIR / f"console-{vm_id}.log"

        def clog(msg: str) -> None:
            try:
                console_log_path.parent.mkdir(parents=True, exist_ok=True)
                with console_log_path.open("a", encoding="utf-8") as f:
                    f.write(f"[{now()}] {msg}\n")
            except Exception:
                pass

        if not rec or not rec.get("vnc_port"):
            clog("reject: missing VM record or vnc_port")
            try: await websocket.close(code=1008)
            except Exception: pass
            return
        proc = VM_PROCS.get(vm_id)
        if proc and proc.poll() is not None:
            clog(f"reject: qemu stopped rc={proc.returncode}")
            try: await websocket.close(code=1011)
            except Exception: pass
            return
        vnc_port = int(rec["vnc_port"])
        clog(f"proxy → raw VNC 127.0.0.1:{vnc_port}")
        try:
            reader, writer = await asyncio.open_connection("127.0.0.1", vnc_port)
            clog("VNC backend connected")
        except Exception as e:
            clog(f"VNC connect failed: {e!r}")
            try: await websocket.close(code=1011)
            except Exception: pass
            return

        async def browser_to_vnc() -> None:
            while True:
                msg = await websocket.receive()
                if msg.get("type") == "websocket.disconnect":
                    break
                data = msg.get("bytes")
                if data is None:
                    text = msg.get("text")
                    if text is None:
                        continue
                    data = text.encode("latin-1", errors="ignore")
                writer.write(data)
                await writer.drain()

        async def vnc_to_browser() -> None:
            while True:
                data = await reader.read(65536)
                if not data:
                    break
                await websocket.send_bytes(data)

        try:
            t1 = asyncio.create_task(browser_to_vnc())
            t2 = asyncio.create_task(vnc_to_browser())
            done, pending = await asyncio.wait({t1, t2}, return_when=asyncio.FIRST_COMPLETED)
            for task in pending:
                task.cancel()
            for task in done:
                try: task.result()
                except Exception as e: clog(f"proxy task error: {e!r}")
            clog("proxy session ended")
        except Exception as e:
            clog(f"proxy fatal: {e!r}")
            try: await websocket.close(code=1011)
            except Exception: pass
        finally:
            try: writer.close(); await writer.wait_closed()
            except Exception: pass

    @app.post("/api/download/{image_id}")
    async def api_download(image_id: str):
        img = CAT_BY_ID.get(image_id)
        if not img:
            raise HTTPException(404, "unknown image id")
        if img.needs_browser:
            try:
                if img.browser_url: webbrowser.open(img.browser_url)
            except Exception: pass
            return {"id": image_id, "manual": True, "browser_url": img.browser_url, "message": img.notes}
        if image_id not in DOWNLOAD_TASKS or DOWNLOAD_TASKS[image_id].done():
            DOWNLOAD_TASKS[image_id] = asyncio.create_task(ensure_download(image_id))
        return {"id": image_id, "engine": "aria2c" if have_aria2c() else "aiohttp", "mirror_count": len(img.mirrors)}

    @app.post("/api/download-all/{filter_name}")
    async def api_download_all(filter_name: str):
        if filter_name not in ("linux", "windows", "bsd", "all"):
            raise HTTPException(400, "filter must be linux|windows|bsd|all")
        selected = [x for x in CATALOG if (filter_name == "all" or x.family == filter_name) and not x.needs_browser]
        for img in selected:
            if img.id not in DOWNLOAD_TASKS or DOWNLOAD_TASKS[img.id].done():
                DOWNLOAD_TASKS[img.id] = asyncio.create_task(ensure_download(img.id))
        return {"started": [x.id for x in selected]}

    @app.get("/api/downloads")
    async def api_downloads():
        return DOWNLOADS

    @app.post("/api/vms/create")
    async def api_vm_create(body: Dict[str, Any] = Body(...)):
        image_id = body.get("image_id")
        if image_id not in CAT_BY_ID:
            raise HTTPException(404, "unknown image id")
        img = CAT_BY_ID[image_id]
        if img.kind not in ("cloud", "iso") or img.family not in ("linux", "windows", "bsd"):
            raise HTTPException(400, "not a bootable VM image")
        if img.needs_browser and not local_image_path(img).exists():
            try:
                if img.browser_url: webbrowser.open(img.browser_url)
            except Exception: pass
            return {"manual": True, "browser_url": img.browser_url}
        job_id = uuid.uuid4().hex
        PROVISION[job_id] = {"job_id": job_id, "image_id": image_id, "phase": "queued", "message": "queued", "will_download": not local_image_path(img).exists()}
        kwargs = {
            "windows_unattended":              bool(body.get("windows_unattended", True)),
            "windows_admin_password":          body.get("windows_admin_password") or None,
            "windows_image_index":             int(body.get("windows_image_index", 2) or 2),
            "windows_enable_rdp":              bool(body.get("windows_enable_rdp", True)),
            "windows_enable_winrm":            bool(body.get("windows_enable_winrm", True)),
            "windows_role_ad":                 bool(body.get("windows_role_ad", False)),
            "windows_domain_name":             body.get("windows_domain_name") or "lab.local",
            "windows_dsrm_password":           body.get("windows_dsrm_password") or None,
            "windows_role_iis":                bool(body.get("windows_role_iis", False)),
            "windows_role_dhcp":               bool(body.get("windows_role_dhcp", False)),
            "windows_role_fileserver":         bool(body.get("windows_role_fileserver", False)),
            "windows_role_dotnet":             bool(body.get("windows_role_dotnet", True)),
            "windows_sharepoint_prereqs":      bool(body.get("windows_sharepoint_prereqs", False)),
            "windows_sharepoint_iso_path":     body.get("windows_sharepoint_iso_path") or None,
            "windows_sharepoint_run_prereqinstaller": bool(body.get("windows_sharepoint_run_prereqinstaller", True)),
            "windows_sharepoint_run_setup":    bool(body.get("windows_sharepoint_run_setup", False)),
            "windows_sharepoint_product_key":  body.get("windows_sharepoint_product_key") or None,
            "windows_sharepoint_ca_port":      int(body.get("windows_sharepoint_ca_port", 20199) or 20199),
            "linux_unattended":                bool(body.get("linux_unattended", True)),
            "linux_username":                  body.get("linux_username") or "qemu",
            "linux_password":                  body.get("linux_password") or None,
            "linux_hostname":                  body.get("linux_hostname") or None,
            "linux_ssh_public_key":            body.get("linux_ssh_public_key") or None,
            "linux_iso_autoinstall":           bool(body.get("linux_iso_autoinstall", True)),
            "linux_inject_repos":              bool(body.get("linux_inject_repos", True)),
            "linux_repo_profile":              body.get("linux_repo_profile") or "global",
            "linux_repo_update":               bool(body.get("linux_repo_update", True)),
            "linux_repo_fix_dns":              bool(body.get("linux_repo_fix_dns", True)),
        }
        asyncio.create_task(provision_vm(image_id, int(body.get("cpus", 2)), int(body.get("ram_mb", 4096)), int(body.get("disk_gb", 60)), job_id, **kwargs))
        return {"job_id": job_id, "will_download": PROVISION[job_id]["will_download"]}

    @app.get("/api/vms/provision/{job_id}")
    async def api_vm_provision(job_id: str):
        rec = PROVISION.get(job_id)
        if not rec:
            raise HTTPException(404, "unknown job id")
        rec = rec.copy()
        rec["download"] = DOWNLOADS.get(rec.get("image_id"))
        return rec

    @app.get("/api/vms")
    async def api_vms():
        return vm_list()

    @app.post("/api/vms/{vm_id}/stop")
    async def api_vm_stop(vm_id: str):
        return {"id": vm_id, "stopped": stop_vm(vm_id)}

    return app


def print_catalog() -> None:
    _dirs()
    for img in CATALOG:
        p = local_image_path(img)
        ready = "ready" if p.exists() else "manual" if img.needs_browser else "missing"
        print(f"{img.id:28s} {img.family:8s} {img.kind:7s} {len(img.mirrors):2d}m {ready:8s} {img.name}")


async def cli_download(image_id: str) -> None:
    p = await ensure_download(image_id)
    print(f"ready: {p}")


async def cli_download_all(filter_name: str) -> None:
    if filter_name not in ("linux", "windows", "bsd", "all"):
        raise SystemExit("filter must be linux|windows|bsd|all")
    tasks = []
    for img in CATALOG:
        if (filter_name == "all" or img.family == filter_name) and not img.needs_browser:
            tasks.append(ensure_download(img.id))
    results = await asyncio.gather(*tasks, return_exceptions=True)
    for img, result in zip([x for x in CATALOG if (filter_name == "all" or x.family == filter_name) and not x.needs_browser], results):
        if isinstance(result, Exception):
            print(f"FAILED {img.id}: {result}", file=sys.stderr)
        else:
            print(f"ok {img.id}: {result}")


def set_data_dir(path: Optional[str]) -> None:
    global DATA_DIR, IMAGES_DIR, VMS_DIR, LOGS_DIR
    if path:
        DATA_DIR = Path(path).expanduser().resolve()
        IMAGES_DIR = DATA_DIR / "images"
        VMS_DIR    = DATA_DIR / "vms"
        LOGS_DIR   = DATA_DIR / "logs"
    _dirs()


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="KVM Auto Downloader + QEMU")
    parser.add_argument("--data-dir", default=None)
    sub = parser.add_subparsers(dest="cmd", required=True)
    ps = sub.add_parser("server")
    ps.add_argument("--host", default="127.0.0.1")
    ps.add_argument("--port", type=int, default=8765)
    ps.add_argument("--bind", default=None, help="QEMU VNC bind host (default 127.0.0.1)")
    sub.add_parser("catalog")
    pd = sub.add_parser("download")
    pd.add_argument("image_id")
    pda = sub.add_parser("download-all")
    pda.add_argument("filter_name")
    args = parser.parse_args(argv)
    set_data_dir(args.data_dir)
    if args.cmd == "catalog":
        print_catalog(); return 0
    if args.cmd == "download":
        asyncio.run(cli_download(args.image_id)); return 0
    if args.cmd == "download-all":
        asyncio.run(cli_download_all(args.filter_name)); return 0
    if args.cmd == "server":
        global BIND_HOST
        if args.bind:
            BIND_HOST = args.bind
        try:
            import uvicorn
        except Exception as e:
            raise SystemExit("Install: pip install fastapi uvicorn aiohttp") from e
        print(f"[{now()}] http://{args.host}:{args.port}  qemu-bind={BIND_HOST}  aria2c={'yes' if have_aria2c() else 'no'}")
        uvicorn.run(build_app(), host=args.host, port=args.port)
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
