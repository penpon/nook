"""
Bot保護ミドルウェア。

botっぽいUser-Agentは許可IPからのみアクセス可能。
通常のブラウザUser-Agentは全IPからアクセス可能。
"""

import ipaddress
import logging
import os
import re
from typing import Callable

from fastapi import Request, status
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

# botと判定するUser-Agentパターン
BOT_PATTERNS = [
    r"curl",
    r"wget",
    r"python-requests",
    r"httpx",
    r"scrapy",
    r"selenium",
    r"puppeteer",
    r"playwright",
    r"bot",
    r"crawler",
    r"spider",
    r"scraper",
    r"headless",
    r"phantom",
    r"slurp",
    r"^$",  # 空のUser-Agent
]

# コンパイル済み正規表現
BOT_REGEX = re.compile("|".join(BOT_PATTERNS), re.IGNORECASE)


def is_bot_user_agent(user_agent: str | None) -> bool:
    """
    User-Agentがbotっぽいか判定。

    Parameters
    ----------
    user_agent : str | None
        User-Agentヘッダー

    Returns
    -------
    bool
        botっぽい場合True
    """
    if not user_agent:
        return True
    return bool(BOT_REGEX.search(user_agent))


def is_allowed_ip(client_ip: str, allowed_ips: list[str]) -> bool:
    """
    IPアドレスが許可リストに含まれるか判定。

    Parameters
    ----------
    client_ip : str
        クライアントのIPアドレス
    allowed_ips : list[str]
        許可IPリスト（CIDR形式対応）

    Returns
    -------
    bool
        許可されている場合True
    """
    try:
        client_addr = ipaddress.ip_address(client_ip)

        # Docker内部ネットワークは常に許可
        docker_networks = [
            ipaddress.ip_network("172.16.0.0/12"),
            ipaddress.ip_network("10.0.0.0/8"),
            ipaddress.ip_network("127.0.0.0/8"),
        ]
        for network in docker_networks:
            if client_addr in network:
                return True

        # 許可IPリストをチェック
        for allowed_ip in allowed_ips:
            try:
                # CIDR形式の場合
                if "/" in allowed_ip:
                    network = ipaddress.ip_network(allowed_ip, strict=False)
                    if client_addr in network:
                        return True
                # 単一IP
                else:
                    if client_addr == ipaddress.ip_address(allowed_ip):
                        return True
            except ValueError:
                logger.warning(f"Invalid IP format in allowed list: {allowed_ip}")
                continue

        return False
    except ValueError:
        logger.warning(f"Invalid client IP: {client_ip}")
        return False


def get_client_ip(request: Request) -> str:
    """
    クライアントの実IPアドレスを取得。

    Parameters
    ----------
    request : Request
        FastAPIリクエスト

    Returns
    -------
    str
        クライアントIPアドレス
    """
    # Nginxのリバースプロキシ経由の場合
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # 最初のIPを取得（クライアントの実IP）
        return forwarded_for.split(",")[0].strip()

    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip

    # 直接アクセスの場合
    return request.client.host if request.client else "unknown"


async def bot_protection_middleware(request: Request, call_next: Callable):
    """
    Bot保護ミドルウェア。

    botっぽいUser-Agentは許可IPからのみアクセス可能。
    通常のブラウザは全IPからアクセス可能。

    Parameters
    ----------
    request : Request
        FastAPIリクエスト
    call_next : Callable
        次のミドルウェア/ハンドラー

    Returns
    -------
    Response
        レスポンス
    """
    user_agent = request.headers.get("User-Agent", "")
    client_ip = get_client_ip(request)

    # User-Agentがbotっぽいか判定
    if is_bot_user_agent(user_agent):
        # 許可IPリストを環境変数から取得
        allowed_ips_str = os.environ.get("ALLOWED_IPS", "164.70.96.2")
        allowed_ips = [ip.strip() for ip in allowed_ips_str.split(",")]

        # 許可IPかチェック
        if not is_allowed_ip(client_ip, allowed_ips):
            logger.warning(
                f"Bot access denied: IP={client_ip}, User-Agent={user_agent}, "
                f"Path={request.url.path}"
            )
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={
                    "error": {
                        "type": "access_denied",
                        "message": "Bot access is not allowed from this IP address",
                        "status_code": 403,
                    }
                },
            )

        logger.info(
            f"Bot access allowed: IP={client_ip}, User-Agent={user_agent}, "
            f"Path={request.url.path}"
        )

    # 通常のアクセスまたは許可されたbotアクセス
    response = await call_next(request)
    return response
