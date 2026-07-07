"""Behavioral (dynamic-analysis) features, parsed from a pre-recorded trace.

Dynamic analysis observes what code actually *does* at runtime (network
connections, file writes, processes spawned) rather than just what it looks
like structurally. That's genuinely useful -- this project's own sqlmap demo
showed static analysis flagging legitimate self-update / OS-compat-shim /
test-fixture code that never actually does anything malicious when run.

CRITICAL SAFETY BOUNDARY -- read before using this module:

    This module only ever *parses* a trace file you already collected. It
    never executes the code under analysis, and neither does anything else in
    this project. Running untrusted, potentially malicious code -- even just
    to observe its behavior -- must happen in a fully isolated, disposable,
    network-off sandbox that is separate from this project's own working
    environment (which has real git/GitHub access and should never run
    unknown code). See ``scripts/sandboxed_trace.sh`` for a template you run
    yourself, on your own isolated machine, to produce the trace file this
    module reads.

Trace format: JSON Lines, one event object per line. Recognized ``type``
values: ``network_connect`` (``host``, ``port``), ``dns_lookup`` (``domain``),
``file_write`` (``path``), ``subprocess`` (``cmd``). Unrecognized event types
are ignored rather than raising, so the format can grow without breaking old
traces.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Dict, Iterable, List

# Paths written outside a sandbox's scratch directory that indicate an actual
# (not just hinted-at) persistence attempt.
PERSISTENCE_PATH_HINTS = (
    "/etc/cron", "crontab", "/etc/systemd", ".bashrc", ".bash_profile",
    "/etc/rc.local", "LaunchAgents", "/etc/init.d",
)

DYNAMIC_FEATURE_NAMES = [
    "num_network_connections",
    "unique_remote_hosts",
    "num_dns_lookups",
    "num_files_written",
    "num_persistence_writes",
    "num_subprocess_spawned",
]


@dataclass
class DynamicFeatures:
    num_network_connections: int = 0
    unique_remote_hosts: int = 0
    num_dns_lookups: int = 0
    num_files_written: int = 0
    num_persistence_writes: int = 0
    num_subprocess_spawned: int = 0

    def to_vector(self) -> List[float]:
        return [float(getattr(self, name)) for name in DYNAMIC_FEATURE_NAMES]

    def to_dict(self) -> Dict[str, float]:
        return asdict(self)


def load_trace(path: str) -> List[dict]:
    """Read a JSON-Lines trace file into a list of event dicts.

    Blank lines and lines that fail to parse as JSON are skipped rather than
    raising, so a partially-written or slightly malformed trace still yields
    whatever events did parse.
    """
    events: List[dict] = []
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return events


def extract_dynamic_features(events: Iterable[dict]) -> DynamicFeatures:
    """Turn a list of trace events into a :class:`DynamicFeatures` vector."""
    features = DynamicFeatures()
    remote_hosts = set()

    for event in events:
        etype = event.get("type")
        if etype == "network_connect":
            features.num_network_connections += 1
            host = event.get("host")
            if host:
                remote_hosts.add(host)
        elif etype == "dns_lookup":
            features.num_dns_lookups += 1
        elif etype == "file_write":
            features.num_files_written += 1
            path = (event.get("path") or "").lower()
            if any(hint.lower() in path for hint in PERSISTENCE_PATH_HINTS):
                features.num_persistence_writes += 1
        elif etype == "subprocess":
            features.num_subprocess_spawned += 1
        # unrecognized event types are ignored, not an error

    features.unique_remote_hosts = len(remote_hosts)
    return features


def combine_vectors(static_vector: List[float], dynamic_vector: List[float]) -> List[float]:
    """Concatenate a static feature vector with a dynamic one for training/scoring."""
    return [*static_vector, *dynamic_vector]
