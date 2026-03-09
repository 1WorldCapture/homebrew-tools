#!/usr/bin/env python3
"""Sync the Homebrew formula to the latest supported FunASR release tag."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
FORMULA_PATH = ROOT / "Formula" / "funasr-onnx.rb"
README_PATH = ROOT / "README.md"
UPSTREAM_GIT_URL = "https://github.com/1WorldCapture/FunASR.git"
ARCHIVE_URL_TEMPLATE = "https://github.com/1WorldCapture/FunASR/archive/refs/tags/{tag}.tar.gz"
TAG_PATTERN = re.compile(r"^ll-(\d+(?:\.\d+)+)$")
FORMULA_STABLE_BLOCK_PATTERN = re.compile(
    r'^(?P<indent>\s*)url\s+"https://github\.com/1WorldCapture/FunASR/archive/refs/tags/(?P<tag>ll-\d+(?:\.\d+)+)\.tar\.gz"\s*$\n'
    r'(?P=indent)version\s+"(?P<version>[^"]+)"\s*$\n'
    r'(?P=indent)sha256\s+"(?P<sha256>[0-9a-f]{64})"\s*$',
    re.MULTILINE,
)
README_TAG_PATTERN = re.compile(r"(- 发布标签：`)(ll-\d+(?:\.\d+)+)(`)")
DOWNLOAD_TIMEOUT_SECONDS = 30
DOWNLOAD_ATTEMPTS = 3


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Update the funasr-onnx formula to the latest upstream ll-x.y tag.",
    )
    parser.add_argument(
        "--tag",
        help="Force a specific upstream ll-x.y tag instead of auto-detecting the latest supported tag.",
    )
    parser.add_argument(
        "--allow-downgrade",
        action="store_true",
        help="Allow a manually requested tag that is older than the current formula version.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report the computed update without writing files.",
    )
    return parser.parse_args()


def emit_outputs(payload: dict[str, Any]) -> None:
    github_output = os.environ.get("GITHUB_OUTPUT")
    normalized = {key: stringify_output(value) for key, value in payload.items()}

    if github_output:
        with open(github_output, "a", encoding="utf-8") as handle:
            for key, value in normalized.items():
                handle.write(f"{key}={value}\n")

    print(json.dumps(normalized, indent=2, sort_keys=True))


def stringify_output(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def parse_version(version: str) -> tuple[int, ...]:
    return tuple(int(part) for part in version.split("."))


def version_from_tag(tag: str) -> str:
    match = TAG_PATTERN.fullmatch(tag)
    if not match:
        raise ValueError(f"Unsupported tag format: {tag}")
    return match.group(1)


def read_formula_metadata() -> dict[str, str]:
    formula = FORMULA_PATH.read_text(encoding="utf-8")
    stable_match = FORMULA_STABLE_BLOCK_PATTERN.search(formula)

    if not stable_match:
        raise RuntimeError("Could not parse Formula/funasr-onnx.rb stable metadata block")

    return {
        "tag": stable_match.group("tag"),
        "version": stable_match.group("version"),
        "sha256": stable_match.group("sha256"),
    }


def fetch_upstream_tags() -> list[str]:
    result = subprocess.run(
        ["git", "ls-remote", "--tags", "--refs", UPSTREAM_GIT_URL],
        check=True,
        capture_output=True,
        text=True,
    )

    tags: list[str] = []
    for line in result.stdout.splitlines():
        _, ref = line.split("\t", maxsplit=1)
        tag = ref.removeprefix("refs/tags/")
        if TAG_PATTERN.fullmatch(tag):
            tags.append(tag)

    if not tags:
        raise RuntimeError("No upstream ll-x.y tags were found")

    return tags


def resolve_target_tag(
    requested_tag: str | None,
    current_tag: str,
    *,
    allow_downgrade: bool,
) -> tuple[str, bool, str, list[str]]:
    tags = fetch_upstream_tags()
    current_version = parse_version(version_from_tag(current_tag))

    if requested_tag:
        requested_tag = requested_tag.strip()
        if requested_tag not in tags:
            raise RuntimeError(f"Requested tag {requested_tag} was not found upstream")

        requested_version = parse_version(version_from_tag(requested_tag))
        if requested_version < current_version and not allow_downgrade:
            raise RuntimeError(
                f"Requested tag {requested_tag} is older than the current formula tag {current_tag}; "
                "re-run with --allow-downgrade if this is intentional"
            )

        return requested_tag, requested_tag != current_tag, "requested-tag", tags

    latest_tag = max(tags, key=lambda tag: parse_version(version_from_tag(tag)))
    latest_version = parse_version(version_from_tag(latest_tag))
    should_update = latest_version > current_version
    reason = "new-version" if should_update else "up-to-date"
    return latest_tag, should_update, reason, tags


def compute_sha256(tag: str) -> tuple[str, str]:
    archive_url = ARCHIVE_URL_TEMPLATE.format(tag=tag)
    last_error: str | None = None

    for attempt in range(1, DOWNLOAD_ATTEMPTS + 1):
        digest = hashlib.sha256()
        process = subprocess.Popen(
            [
                "curl",
                "-fsSL",
                "--connect-timeout",
                str(DOWNLOAD_TIMEOUT_SECONDS),
                "--max-time",
                str(DOWNLOAD_TIMEOUT_SECONDS * 4),
                archive_url,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        assert process.stdout is not None
        for chunk in iter(lambda: process.stdout.read(1024 * 1024), b""):
            digest.update(chunk)

        stderr = b""
        if process.stderr is not None:
            stderr = process.stderr.read()

        if process.wait() == 0:
            return archive_url, digest.hexdigest()

        last_error = stderr.decode("utf-8", errors="replace").strip() or "curl exited with a non-zero status"
        if attempt == DOWNLOAD_ATTEMPTS:
            break
        time.sleep(attempt)

    raise RuntimeError(f"Failed to download {archive_url}: {last_error}")


def replace_once(pattern: re.Pattern[str], text: str, repl: str, *, label: str) -> str:
    updated, count = pattern.subn(repl, text, count=1)
    if count != 1:
        raise RuntimeError(f"Expected to replace {label} exactly once")
    return updated


def update_formula(tag: str, version: str, sha256: str) -> None:
    formula = FORMULA_PATH.read_text(encoding="utf-8")
    stable_match = FORMULA_STABLE_BLOCK_PATTERN.search(formula)
    if not stable_match:
        raise RuntimeError("Could not find the stable metadata block in Formula/funasr-onnx.rb")

    indent = stable_match.group("indent")
    replacement = "\n".join(
        [
            f'{indent}url "{ARCHIVE_URL_TEMPLATE.format(tag=tag)}"',
            f'{indent}version "{version}"',
            f'{indent}sha256 "{sha256}"',
        ]
    )

    updated = formula[: stable_match.start()] + replacement + formula[stable_match.end() :]
    FORMULA_PATH.write_text(updated, encoding="utf-8")


def update_readme(tag: str) -> None:
    readme = README_PATH.read_text(encoding="utf-8")
    updated = replace_once(
        README_TAG_PATTERN,
        readme,
        r"\g<1>" + tag + r"\g<3>",
        label="README tag",
    )
    README_PATH.write_text(updated, encoding="utf-8")


def main() -> int:
    args = parse_args()
    current = read_formula_metadata()
    target_tag, should_update, reason, upstream_tags = resolve_target_tag(
        args.tag,
        current["tag"],
        allow_downgrade=args.allow_downgrade,
    )
    target_version = version_from_tag(target_tag)

    payload: dict[str, Any] = {
        "updated": False,
        "reason": reason,
        "previous_tag": current["tag"],
        "previous_version": current["version"],
        "tag": target_tag,
        "version": target_version,
        "sha256": current["sha256"],
        "archive_url": ARCHIVE_URL_TEMPLATE.format(tag=target_tag),
        "mode": "dry-run" if args.dry_run else "write",
        "upstream_tag_count": len(upstream_tags),
    }

    if not should_update:
        archive_url, current_tag_sha256 = compute_sha256(target_tag)
        if current_tag_sha256 == current["sha256"]:
            emit_outputs(payload)
            return 0

        payload.update(
            {
                "updated": True,
                "reason": "checksum-refresh",
                "sha256": current_tag_sha256,
                "archive_url": archive_url,
            }
        )
    else:
        archive_url, target_sha256 = compute_sha256(target_tag)
        payload.update(
            {
                "updated": True,
                "sha256": target_sha256,
                "archive_url": archive_url,
            }
        )

    if not args.dry_run:
        update_formula(target_tag, target_version, target_sha256)
        update_readme(target_tag)

    emit_outputs(payload)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # pragma: no cover - workflow-friendly failure path
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
