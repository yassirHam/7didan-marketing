"""Minimal Odoo XML-RPC client (standard library only)."""
from __future__ import annotations

import time
import xmlrpc.client
from typing import Any


class OdooError(RuntimeError):
    pass


class Odoo:
    def __init__(self, url: str, db: str, login: str, password: str):
        self.url, self.db, self.login, self.password = url.rstrip("/"), db, login, password
        self._common = xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/common", allow_none=True)
        self._object = xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/object", allow_none=True)
        self.uid = self._common.authenticate(db, login, password, {})
        if not self.uid:
            raise OdooError(f"Odoo rejected the credentials for {login!r}.")

    def call(self, model: str, method: str, *args: Any, **kwargs: Any) -> Any:
        return self._object.execute_kw(self.db, self.uid, self.password, model, method, list(args), kwargs)

    def search_read(self, model: str, domain: list, fields: list[str], **kwargs: Any) -> list[dict]:
        return self.call(model, "search_read", domain, fields=fields, **kwargs)

    def ref(self, xmlid: str) -> int:
        module, name = xmlid.split(".", 1)
        rows = self.search_read("ir.model.data", [("module", "=", module), ("name", "=", name)], ["res_id"])
        if not rows:
            raise OdooError(f"External ID {xmlid} not found.")
        return rows[0]["res_id"]


def wait_for_odoo(url: str, timeout: float = 180) -> None:
    """Block until the Odoo RPC endpoint answers."""
    deadline = time.monotonic() + timeout
    proxy = xmlrpc.client.ServerProxy(f"{url.rstrip('/')}/xmlrpc/2/common")
    while True:
        try:
            proxy.version()
            return
        except (OSError, xmlrpc.client.ProtocolError):
            if time.monotonic() > deadline:
                raise OdooError(f"Odoo did not answer at {url} within {timeout:.0f}s.")
            time.sleep(2)
