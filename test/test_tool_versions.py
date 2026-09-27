"""Regression coverage for tooling drift and interpreter-compatible hook pins."""

from __future__ import annotations

import shutil
import re
from pathlib import Path

import pytest

from scripts.check_tool_versions import check

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def tooling_config(tmp_path: Path) -> Path:
    for name in (
        "pyproject.toml",
        ".pre-commit-config.yaml",
        "tox.ini",
        ".github/workflows/ci.yml",
    ):
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, target)
    return tmp_path


def test_current_tooling_config_agrees() -> None:
    assert check(ROOT) == []


@pytest.mark.parametrize("marker", ["python_version < '3.11'", "python_version >= '3.11'"])
def test_missing_hook_interpreter_branch_is_detected(tooling_config: Path, marker: str) -> None:
    config = tooling_config / ".pre-commit-config.yaml"
    config.write_text(config.read_text().replace(marker, "python_version >= '3.99'"))
    errors = check(tooling_config)
    assert any("mypy hook dependencies: missing" in error and marker in error for error in errors)


def test_stale_ruff_hook_revision_is_detected(tooling_config: Path) -> None:
    config = tooling_config / ".pre-commit-config.yaml"
    config.write_text(
        re.sub(
            r"(repo: https://github.com/astral-sh/ruff-pre-commit\n\s+rev:) [^\n]+",
            r"\1 v0.0.0",
            config.read_text(),
        )
    )
    assert any(
        "ruff hook revision:" in error and "v0.0.0" in error for error in check(tooling_config)
    )


def test_expanded_ruff_cli_scope_is_detected(tooling_config: Path) -> None:
    config = tooling_config / "pyproject.toml"
    config.write_text(config.read_text().replace('["*.py", "*.pyi"]', '["*.py", "*.pyi", "*.md"]'))
    assert any("Ruff CLI file scope" in error for error in check(tooling_config))
