from __future__ import annotations

import ast
import hashlib
import json
import re
import subprocess
import sys
import unicodedata
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from urllib.parse import unquote_plus

TEXT_EXTENSIONS = {
    ".py",
    ".json",
    ".md",
    ".toml",
    ".example",
    ".yml",
    ".yaml",
    ".txt",
    ".ini",
    ".cfg",
    ".conf",
    ".env",
}
EXACT_CREDENTIAL_KEYS = {
    "opendartapikey",
    "naverclientid",
    "naverclientsecret",
    "llmapikey",
}
GENERIC_CREDENTIAL_KEYS = {
    "apikey",
    "accesstoken",
    "authtoken",
    "bearertoken",
    "clientsecret",
    "authorization",
    "xamzsignature",
    "xapikey",
}
ASSIGNMENT_RE = re.compile(
    r"^\s*(?:export\s+)?[\"']?(?P<key>[A-Za-z0-9_.% -]+)[\"']?\s*(?P<op>[:=])\s*(?P<value>.+?)\s*,?\s*$"
)
WINDOWS_ABSOLUTE_PATH_RE = re.compile(r"(?<![A-Za-z])[A-Za-z]:[\\/]")
UNC_PATH_RE = re.compile(r"(?<!:)//[A-Za-z0-9_.-]+/|\\\\[A-Za-z0-9_.-]+[\\/]")
POSIX_ABSOLUTE_PATH_RE = re.compile(r"(^|[\s\"'(=])/(root|opt|workspace|home|Users|etc|var|tmp)(/|$)")


class SecretScanError(RuntimeError):
    """Raised when the scanner cannot safely inspect tracked files."""


@dataclass(frozen=True, order=True)
class SecretFinding:
    path: str
    line: int
    rule_id: str


def list_tracked_files(repo_root: Path) -> tuple[Path, ...]:
    root = repo_root.resolve()
    try:
        completed = subprocess.run(
            ["git", "ls-files", "-z"],
            cwd=root,
            timeout=10,
            shell=False,
            check=False,
            capture_output=True,
        )
    except (OSError, subprocess.TimeoutExpired):
        raise SecretScanError("secret scan failed") from None
    if completed.returncode != 0:
        raise SecretScanError("secret scan failed")
    paths: list[Path] = []
    for raw_path in completed.stdout.split(b"\0"):
        if not raw_path:
            continue
        try:
            text_path = raw_path.decode("utf-8")
        except UnicodeDecodeError:
            raise SecretScanError("secret scan failed") from None
        if Path(text_path).is_absolute():
            raise SecretScanError("secret scan failed")
        path = (root / text_path).resolve()
        try:
            path.relative_to(root)
        except ValueError:
            raise SecretScanError("secret scan failed") from None
        paths.append(path)
    return tuple(paths)


def scan_paths(paths: Iterable[Path], *, repo_root: Path) -> list[SecretFinding]:
    root = repo_root.resolve()
    findings: list[SecretFinding] = []
    for path in paths:
        absolute, relative = _safe_relative_path(path, root)
        if not _is_scannable_text_path(relative):
            continue
        try:
            raw = absolute.read_bytes()
            text = raw.decode("utf-8")
        except (OSError, UnicodeDecodeError):
            raise SecretScanError("secret scan failed") from None
        rel_text = relative.as_posix()
        findings.extend(_credential_findings_for_text(text, relative_path=relative, rel_text=rel_text))
        for line_number, line in enumerate(text.splitlines(), start=1):
            if _is_public_surface(relative) and _contains_public_absolute_path(line):
                findings.append(SecretFinding(path=rel_text, line=line_number, rule_id="public_absolute_path"))
    return sorted(findings)


def _safe_relative_path(path: Path, root: Path) -> tuple[Path, Path]:
    absolute = path if path.is_absolute() else root / path
    resolved = absolute.resolve()
    try:
        relative = resolved.relative_to(root)
    except ValueError:
        raise SecretScanError("secret scan failed") from None
    return resolved, relative


def _is_scannable_text_path(relative: Path) -> bool:
    return relative.name.startswith(".env") or relative.suffix in TEXT_EXTENSIONS


def _is_public_surface(relative: Path) -> bool:
    parts = relative.parts
    if relative.as_posix() in {"README.md", ".env.example", "pyproject.toml"}:
        return True
    if parts and parts[0] == "data" and relative.suffix == ".json":
        return True
    if len(parts) >= 2 and parts[0] == ".github" and relative.suffix in {".yml", ".yaml"}:
        return True
    return False


def _credential_findings_for_text(text: str, *, relative_path: Path, rel_text: str) -> list[SecretFinding]:
    if relative_path.suffix == ".py":
        return _python_credential_findings(text, rel_text=rel_text)
    if relative_path.suffix == ".json":
        findings = _json_credential_findings(text, rel_text=rel_text)
        if findings is not None:
            return findings
    findings: list[SecretFinding] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        rule = _credential_assignment_rule(line, relative_path=relative_path)
        if rule is not None:
            findings.append(SecretFinding(path=rel_text, line=line_number, rule_id=rule))
    return findings


def _python_credential_findings(text: str, *, rel_text: str) -> list[SecretFinding]:
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return []
    findings: list[SecretFinding] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                finding = _python_assignment_finding(target, node.value, node.lineno, rel_text)
                if finding is not None:
                    findings.append(finding)
        elif isinstance(node, ast.AnnAssign):
            finding = _python_assignment_finding(node.target, node.value, node.lineno, rel_text)
            if finding is not None:
                findings.append(finding)
    return sorted(findings)


def _python_assignment_finding(target: ast.expr, value: ast.expr | None, line_number: int, rel_text: str) -> SecretFinding | None:
    if not isinstance(target, ast.Name) or value is None:
        return None
    if not _is_credential_key(target.id):
        return None
    if not isinstance(value, ast.Constant) or not isinstance(value.value, str) or not value.value.strip():
        return None
    if _is_environment_reference(value.value):
        return None
    return SecretFinding(path=rel_text, line=line_number, rule_id="non_empty_credential_assignment")


def _json_credential_findings(text: str, *, rel_text: str) -> list[SecretFinding] | None:
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return None
    lines = text.splitlines()
    findings: list[SecretFinding] = []
    for key, value in _walk_json_object(parsed):
        if not _is_credential_key(key):
            continue
        if isinstance(value, str) and value.strip() and not _is_environment_reference(value):
            findings.append(
                SecretFinding(path=rel_text, line=_line_for_json_key(lines, key), rule_id="non_empty_credential_assignment")
            )
    return sorted(findings)


def _walk_json_object(value: Any) -> Iterable[tuple[str, Any]]:
    if isinstance(value, dict):
        for key, nested in value.items():
            if isinstance(key, str):
                yield key, nested
            yield from _walk_json_object(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from _walk_json_object(nested)


def _line_for_json_key(lines: list[str], key: str) -> int:
    quoted = json.dumps(key, ensure_ascii=False)
    for index, line in enumerate(lines, start=1):
        if quoted in line or key in line:
            return index
    return 1


def _credential_assignment_rule(line: str, *, relative_path: Path) -> str | None:
    match = ASSIGNMENT_RE.match(line)
    if match is None:
        return None
    raw_key = match.group("key").strip().strip("\"'")
    if "." in raw_key:
        return None
    if match.group("op") == ":" and re.search(r"\s=\s", match.group("value")):
        return None
    if not _is_credential_key(raw_key):
        return None
    if not _is_non_empty_literal(match.group("value"), raw_key=raw_key, relative_path=relative_path):
        return None
    return "non_empty_credential_assignment"


def _is_credential_key(value: str) -> bool:
    key = _normalize_key(value)
    return key in EXACT_CREDENTIAL_KEYS or key in GENERIC_CREDENTIAL_KEYS or _has_credential_suffix(key)


def _normalize_key(value: str) -> str:
    decoded = unquote_plus(value.strip().strip("\"'"))
    normalized = unicodedata.normalize("NFKC", decoded)
    return re.sub(r"[\s_.-]+", "", normalized.casefold())


def _has_credential_suffix(key: str) -> bool:
    return any(key.endswith(suffix) for suffix in GENERIC_CREDENTIAL_KEYS)


def _is_non_empty_literal(value: str, *, raw_key: str, relative_path: Path) -> bool:
    cleaned = value.strip().rstrip(",").strip()
    if not cleaned:
        return False
    if "#" in cleaned and not cleaned.startswith(("'", '"')):
        cleaned = cleaned.split("#", 1)[0].strip()
    if cleaned in {"''", '""', "null", "None"}:
        return False
    if _is_environment_reference(cleaned):
        return False
    if relative_path.suffix == ".py":
        return cleaned[0] in {"'", '"'}
    if cleaned[0] in {"'", '"'}:
        quote = cleaned[0]
        if len(cleaned) < 2 or quote not in cleaned[1:]:
            return False
        content = cleaned[1 : cleaned.rfind(quote)]
        return bool(content.strip()) and not _is_environment_reference(content)
    return bool(cleaned)


def _is_environment_reference(value: str) -> bool:
    stripped = value.strip()
    return stripped.startswith(("${", "os.getenv", "os.environ"))


def _contains_public_absolute_path(line: str) -> bool:
    lowered = line.lower()
    return (
        "file://" in lowered
        or bool(WINDOWS_ABSOLUTE_PATH_RE.search(line))
        or bool(UNC_PATH_RE.search(line))
        or bool(POSIX_ABSOLUTE_PATH_RE.search(line))
    )


def normalized_line_hash(line: str) -> str:
    normalized = " ".join(line.split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    repo_root = Path(argv[0]) if argv else Path.cwd()
    try:
        findings = scan_paths(list_tracked_files(repo_root), repo_root=repo_root)
    except SecretScanError:
        sys.stdout.write(json.dumps({"status": "error", "message": "secret scan failed"}, sort_keys=True))
        sys.stdout.write("\n")
        return 2
    sys.stdout.write(json.dumps([asdict(finding) for finding in findings], ensure_ascii=False, sort_keys=True))
    sys.stdout.write("\n")
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
