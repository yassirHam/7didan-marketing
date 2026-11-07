"""One-command setup of the 7didan CRM stack:  python scripts/setup.py

1. Start PostgreSQL and create the Odoo database with the CRM app (first run only).
2. Start Odoo, secure the admin account and configure CRM (scripts/configure_odoo.py).
3. Create the reporting schema, the idempotency index, the reporting views and the DB roles.
4. Start n8n, which imports and activates the workflow on boot.
Every step is idempotent, so the script can be re-run at any time.
"""
from __future__ import annotations

import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.configure_odoo import configure  # noqa: E402
from scripts.env import ROOT, compose, load_env, psql  # noqa: E402
from scripts.odoo_rpc import Odoo, OdooError, wait_for_odoo  # noqa: E402

ODOO_URL = "http://localhost:8069"
N8N_HEALTH = "http://localhost:5678/healthz"
DEFAULT_ADMIN_PASSWORD = "admin"  # set by Odoo when the database is created


def wait_healthy_db(env: dict[str, str], timeout: float = 90) -> None:
    deadline = time.monotonic() + timeout
    while compose("exec", "-T", "db", "pg_isready", "-U", env["POSTGRES_USER"], check=False).returncode != 0:
        if time.monotonic() > deadline:
            raise SystemExit("PostgreSQL did not become ready.")
        time.sleep(2)


def ensure_database(env: dict[str, str]) -> None:
    exists = psql(env, f"SELECT 1 FROM pg_database WHERE datname = '{env['ODOO_DB']}'", database="postgres")
    if exists:
        print(f"Odoo database {env['ODOO_DB']!r} already exists")
        return
    print(f"Creating Odoo database {env['ODOO_DB']!r} with the CRM app (takes a few minutes)")
    compose("run", "--rm", "odoo", "odoo", "-d", env["ODOO_DB"], "-i", "crm",
            "--without-demo=all", "--stop-after-init")


def admin_session(env: dict[str, str]) -> Odoo:
    """Log in as admin; on first run replace Odoo's default admin password with the configured one."""
    login, password = env["ODOO_ADMIN_LOGIN"], env["ODOO_ADMIN_PASSWORD"]
    try:
        return Odoo(ODOO_URL, env["ODOO_DB"], login, password)
    except OdooError:
        odoo = Odoo(ODOO_URL, env["ODOO_DB"], login, DEFAULT_ADMIN_PASSWORD)
        odoo.call("res.users", "write", [odoo.uid], {"password": password})
        print("  default admin password replaced")
        return Odoo(ODOO_URL, env["ODOO_DB"], login, password)


def apply_sql(env: dict[str, str]) -> None:
    print("Applying reporting schema, views and roles")
    variables = {"dbname": env["ODOO_DB"], "logger_password": env["N8N_LOGGER_PASSWORD"],
                 "reader_password": env["POWERBI_READER_PASSWORD"]}
    for name in ("reporting.sql", "reporting_views.sql", "roles.sql"):
        psql(env, (ROOT / "database" / name).read_text(encoding="utf-8"), variables=variables)


def wait_for_n8n(timeout: float = 120) -> None:
    deadline = time.monotonic() + timeout
    while True:
        try:
            with urllib.request.urlopen(N8N_HEALTH, timeout=5) as resp:
                if resp.status == 200:
                    return
        except OSError:
            pass
        if time.monotonic() > deadline:
            raise SystemExit("n8n did not become healthy; see `docker compose logs n8n`.")
        time.sleep(2)


def main() -> None:
    env = load_env()
    compose("up", "-d", "db")
    wait_healthy_db(env)
    ensure_database(env)
    compose("up", "-d", "odoo")
    wait_for_odoo(ODOO_URL)
    configure(admin_session(env), env["ODOO_INTEGRATION_LOGIN"], env["ODOO_INTEGRATION_PASSWORD"])
    apply_sql(env)
    compose("up", "-d", "--force-recreate", "n8n")
    wait_for_n8n()
    print("Ready: Odoo http://localhost:8069  n8n http://localhost:5678  webhook", env["N8N_WEBHOOK_URL"])


if __name__ == "__main__":
    main()
