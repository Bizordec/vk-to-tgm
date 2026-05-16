from __future__ import annotations

from typing import TYPE_CHECKING

from loguru import logger
from telethon import connection

if TYPE_CHECKING:
    from typing import Any, Literal, NotRequired, TypedDict

    class TgmProxyConfig(TypedDict):
        proxy: NotRequired[dict[str, Any]]
        connection: NotRequired[connection.Connection]

def get_tgm_proxy_config(
    proxy_addr: str,
    proxy_port: int,
    proxy_user: str,
    proxy_pass: str,
    proxy_type: Literal["socks5", "socks4", "http", "mtproto"] | None = None,
    proxy_mtproto_secret: str | None = None,
    proxy_mtproto_connection: Literal[
        "abridged",
        "intermediate",
        "randomized_intermediate",
    ] = "randomized_intermediate",
    *,
    proxy_rdns: bool = True,
) -> TgmProxyConfig:
    if not proxy_addr:
        return {}

    if not proxy_type:
        proxy_type = "socks5"


    if proxy_type == "mtproto":
        if not proxy_mtproto_secret:
            logger.warning("MTProto proxy secret is not set, skipping proxy")
            return {}

        proxy_connection = connection.ConnectionTcpMTProxyRandomizedIntermediate
        match proxy_mtproto_connection:
            case "abridged":
                proxy_connection = connection.ConnectionTcpMTProxyAbridged
            case "intermediate":
                proxy_connection = connection.ConnectionTcpMTProxyIntermediate
        return {
            "proxy": (proxy_addr, proxy_port, proxy_mtproto_secret),
            "connection": proxy_connection,
        }

    proxy = {
        "proxy_type": proxy_type,
        "addr": proxy_addr,
        "port": proxy_port,
        "rdns": proxy_rdns,
    }
    if proxy_user:
        proxy["username"] = proxy_user
    if proxy_pass:
        proxy["password"] = proxy_pass
    return {
        "proxy": proxy,
    }
