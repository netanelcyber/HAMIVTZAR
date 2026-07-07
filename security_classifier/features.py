"""Static, structural feature extraction for Python source code.

Every feature comes from parsing the AST and inspecting string literals —
analyzed source is **never executed**. This is the same style of static
feature engineering used in published malicious-package-detection research
(suspicious imports, dynamic-execution calls, obfuscation indicators, network
and persistence signals) rather than treating raw source as an opaque blob.
"""

from __future__ import annotations

import ast
import math
from collections import Counter
from dataclasses import asdict, dataclass
from typing import Dict, List, Optional

# Presence of any one of these is a weak signal on its own (plenty of benign
# systems code imports `os`/`subprocess`); the classifier weighs them together
# with the other structural features rather than gating on any single one.
WATCHED_IMPORTS = (
    "socket", "subprocess", "os", "ctypes", "base64", "marshal", "pickle",
    "shutil", "winreg", "urllib", "requests", "ftplib", "telnetlib",
)

PERSISTENCE_HINTS = (
    "crontab", "/etc/cron", "startup", "hkey_", "launchagents",
    "systemd", ".bashrc", ".bash_profile", "registry",
)

FEATURE_NAMES = [
    "num_lines",
    "num_functions",
    "num_imports",
    "suspicious_import_count",
    "has_eval_exec",
    "has_subprocess_shell_true",
    "has_os_system",
    "has_base64_decode",
    "has_network_connect",
    "has_persistence_hint",
    "max_string_entropy",
    "long_string_count",
]


def _shannon_entropy(s: str) -> float:
    if not s:
        return 0.0
    counts = Counter(s)
    length = len(s)
    return -sum((n / length) * math.log2(n / length) for n in counts.values())


@dataclass
class Features:
    num_lines: int = 0
    num_functions: int = 0
    num_imports: int = 0
    suspicious_import_count: int = 0
    has_eval_exec: int = 0
    has_subprocess_shell_true: int = 0
    has_os_system: int = 0
    has_base64_decode: int = 0
    has_network_connect: int = 0
    has_persistence_hint: int = 0
    max_string_entropy: float = 0.0
    long_string_count: int = 0

    def to_vector(self) -> List[float]:
        return [float(getattr(self, name)) for name in FEATURE_NAMES]

    def to_dict(self) -> Dict[str, float]:
        return asdict(self)


class _Visitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.num_functions = 0
        self.num_imports = 0
        self.suspicious_import_count = 0
        self.has_eval_exec = False
        self.has_subprocess_shell_true = False
        self.has_os_system = False
        self.has_base64_decode = False
        self.has_network_connect = False
        self.string_literals: List[str] = []

    def visit_FunctionDef(self, node: ast.AST) -> None:
        self.num_functions += 1
        self.generic_visit(node)

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            self.num_imports += 1
            root = alias.name.split(".")[0]
            if root in WATCHED_IMPORTS:
                self.suspicious_import_count += 1
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        self.num_imports += 1
        if node.module and node.module.split(".")[0] in WATCHED_IMPORTS:
            self.suspicious_import_count += 1
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        name = self._callable_name(node.func)
        root = self._attr_root(node.func)

        # eval/exec/compile are builtins, called bare (`compile(...)`), not as
        # an attribute of some other object -- `re.compile(...)` is an
        # unrelated, harmless regex compilation and must not count here.
        if isinstance(node.func, ast.Name) and name in ("eval", "exec", "compile"):
            self.has_eval_exec = True
        if name == "system" and root == "os":
            self.has_os_system = True
        if name == "connect":
            self.has_network_connect = True
        if name in ("b64decode", "b64encode"):
            self.has_base64_decode = True
        if name in ("Popen", "run", "call"):
            for kw in node.keywords:
                if (
                    kw.arg == "shell"
                    and isinstance(kw.value, ast.Constant)
                    and kw.value.value is True
                ):
                    self.has_subprocess_shell_true = True

        self.generic_visit(node)

    def visit_Constant(self, node: ast.Constant) -> None:
        if isinstance(node.value, str):
            self.string_literals.append(node.value)
        self.generic_visit(node)

    @staticmethod
    def _callable_name(func: ast.AST) -> Optional[str]:
        if isinstance(func, ast.Name):
            return func.id
        if isinstance(func, ast.Attribute):
            return func.attr
        return None

    @staticmethod
    def _attr_root(func: ast.AST) -> Optional[str]:
        if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
            return func.value.id
        return None


def extract_features(source: str) -> Features:
    """Parse ``source`` and return its structural :class:`Features`.

    Only ever parses (:func:`ast.parse`) and walks the resulting tree — the
    source is never executed. Source that fails to parse (syntax errors,
    non-UTF-8 noise) yields a near-empty feature vector instead of raising.
    """
    features = Features(num_lines=source.count("\n") + 1)
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return features

    visitor = _Visitor()
    visitor.visit(tree)

    features.num_functions = visitor.num_functions
    features.num_imports = visitor.num_imports
    features.suspicious_import_count = visitor.suspicious_import_count
    features.has_eval_exec = int(visitor.has_eval_exec)
    features.has_subprocess_shell_true = int(visitor.has_subprocess_shell_true)
    features.has_os_system = int(visitor.has_os_system)
    features.has_base64_decode = int(visitor.has_base64_decode)
    features.has_network_connect = int(visitor.has_network_connect)

    lower_source = source.lower()
    features.has_persistence_hint = int(
        any(hint in lower_source for hint in PERSISTENCE_HINTS)
    )

    long_strings = [s for s in visitor.string_literals if len(s) >= 40]
    features.long_string_count = len(long_strings)
    features.max_string_entropy = max(
        (_shannon_entropy(s) for s in long_strings), default=0.0
    )

    return features
