"""Shared helpers: .env loading, docker compose and psql calls."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load_env(path: Path = ROOT / ".env") -> dict[str, str]:
    """Read KEY=VALUE lines from .env; real environment variables take precedence."""
    if not path.exists():
        raise SystemExit(f"Missing {path}. Copy .env.example to .env and fill in the values.")
    values: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.split(" #", 1)[0].strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    values.update({k: v for k, v in os.environ.items() if k in values})
    return values


def compose(*args: str, input_text: str | None = None, check: bool = True) -> subprocess.CompletedProcess:
    """Run `docker compose <args>` from the project root."""
    return subprocess.run(
        ["docker", "compose", *args], cwd=ROOT, input=input_text, text=True,
        capture_output=True, check=check,
    )


def psql(env: dict[str, str], sql: str, database: str | None = None, variables: dict[str, str] | None = None) -> str:
    """Run SQL inside the db container as the Postgres owner and return stdout."""
    args = ["exec", "-T", "db", "psql", "-v", "ON_ERROR_STOP=1", "-qtA",
            "-U", env["POSTGRES_USER"], "-d", database or env["ODOO_DB"]]
    for key, value in (variables or {}).items():
        args += ["-v", f"{key}={value}"]
    return compose(*args, input_text=sql).stdout.strip()
