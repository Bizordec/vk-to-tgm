from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any, Literal

def get_tgm_proxy_config(
    proxy_addr: str,
    proxy_port: int,
    proxy_user: str,
    proxy_pass: str,
    proxy_type: Literal["socks5", "socks4", "http"] = "socks5",
    *,
    proxy_rdns: bool = True,
) -> dict[str, Any] | None:
    if not proxy_addr:
        return None

    proxy = {
        "proxy_type": proxy_type,
        "addr": proxy_addr,
        "rdns": proxy_rdns,
    }
    if proxy_port:
        proxy["port"] = proxy_port
    if proxy_user:
        proxy["username"] = proxy_user
    if proxy_pass:
        proxy["password"] = proxy_pass
    return proxy
