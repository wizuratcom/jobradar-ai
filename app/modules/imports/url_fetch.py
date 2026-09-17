import ipaddress
import socket
from urllib.parse import urljoin, urlparse

import httpx


class URLImportError(Exception):
    pass


def _validate_host(host: str) -> None:
    try:
        addresses = {item[4][0] for item in socket.getaddrinfo(host, None)}
    except socket.gaierror as exc:
        raise URLImportError("Could not resolve vacancy URL host.") from exc
    for address in addresses:
        ip = ipaddress.ip_address(address)
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
            or ip.is_unspecified
        ):
            raise URLImportError("Private or reserved URL addresses are not allowed.")


async def fetch_public_url(url: str) -> tuple[str, str, str]:
    current = url
    async with httpx.AsyncClient(timeout=httpx.Timeout(10.0), follow_redirects=False) as client:
        for _ in range(4):
            parsed = urlparse(current)
            if parsed.scheme not in {"http", "https"} or not parsed.hostname:
                raise URLImportError("Only public http/https URLs are supported.")
            _validate_host(parsed.hostname)
            response = await client.get(current, headers={"User-Agent": "JobRadar/0.6"})
            if response.is_redirect:
                location = response.headers.get("location")
                if not location:
                    raise URLImportError("Vacancy URL redirect had no target.")
                current = urljoin(current, location)
                continue
            if response.status_code >= 400:
                raise URLImportError(
                    "Could not access this vacancy automatically. Paste the vacancy text instead."
                )
            content_type = response.headers.get("content-type", "").casefold()
            if not any(
                value in content_type for value in ("text/html", "application/json", "text/plain")
            ):
                raise URLImportError("Vacancy URL returned an unsupported content type.")
            if len(response.content) > 2_000_000:
                raise URLImportError("Vacancy response is too large.")
            return current, content_type, response.text
    raise URLImportError("Too many URL redirects.")
