"""
Network helpers — extract real client IP from a Render-fronted request.

Render (and most reverse-proxy deployments) terminates TLS at the
load balancer, so `request.client.host` is the proxy IP, not the
real client. Pulling from the leftmost X-Forwarded-For entry recovers
the real client. We validate the candidate as IPv4/IPv6 to reject
header-injection attempts.
"""
import ipaddress
from typing import Optional

from fastapi import Request


def get_client_ip(request: Request) -> Optional[str]:
    """Return the client's real IP, or None if it cannot be determined.

    Order:
    1. Leftmost entry in the X-Forwarded-For header (validated as IP).
    2. request.client.host (whatever uvicorn saw — usually the proxy).
    """
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        # X-Forwarded-For: client, proxy1, proxy2 — the client is leftmost.
        candidate = forwarded.split(",", 1)[0].strip()
        if candidate and _is_valid_ip(candidate):
            return candidate

    if request.client and request.client.host:
        return request.client.host

    return None


def _is_valid_ip(value: str) -> bool:
    try:
        ipaddress.ip_address(value)
        return True
    except ValueError:
        return False
