"""Requests to the HTTP APIs that `api` servers and OData services name."""

import ipaddress
import socket

import requests
from requests.adapters import HTTPAdapter
from urllib3.connection import HTTPConnection, HTTPSConnection
from urllib3.connectionpool import HTTPConnectionPool, HTTPSConnectionPool
from urllib3.exceptions import NewConnectionError

from datacontract.config import Config


def api_headers(config: Config) -> dict[str, str]:
    """The configured credential headers."""
    headers = {}
    if config.get_api_header_authorization() is not None:
        headers["Authorization"] = config.get_api_header_authorization()
    if config.get_api_header_x_api_key() is not None:
        headers["X-API-Key"] = config.get_api_header_x_api_key()
    return headers


class ApiSession(requests.Session):
    """Keep Requests' redirect policy without introducing .netrc credentials, and drop the credential headers
    on a redirect to another host."""

    def rebuild_auth(self, prepared_request: requests.PreparedRequest, response: requests.Response) -> None:
        if self.should_strip_auth(response.request.url, prepared_request.url):
            prepared_request.headers.pop("Authorization", None)
            prepared_request.headers.pop("X-API-Key", None)


class PrivateAddressRefused(NewConnectionError):
    def __init__(self, conn, host: str):
        self.message = (
            f"Refused to connect to {host}: a posted data contract may not reach a private network address. "
            f"Start the API server with --allow-private-network to allow it."
        )
        super().__init__(conn, self.message)


def _is_public(address: str) -> bool:
    address = ipaddress.ip_address(address)
    # IPv4-mapped, NAT64, IPv4-compatible and IPv4-translated addresses reach the IPv4 address in their low 32 bits.
    if address.version == 6 and any(
        address in ipaddress.ip_network(prefix)
        for prefix in ("::ffff:0:0/96", "64:ff9b::/96", "::/96", "::ffff:0:0:0/96")
    ):
        address = ipaddress.IPv4Address(int(address) & 0xFFFFFFFF)
    return address.is_global


class _PublicPeerOnly:
    # Refuses a private address before connecting, so a refusal tells nothing about the private network's ports or
    # addresses, and checks the address actually connected to, so DNS rebinding cannot get around it.
    def _new_conn(self):
        try:
            resolved = [info[4][0] for info in socket.getaddrinfo(self.host, self.port, type=socket.SOCK_STREAM)]
        except OSError:
            resolved = []  # urllib3 reports the resolution failure
        if not all(_is_public(address) for address in resolved):
            raise PrivateAddressRefused(self, self.host)
        sock = super()._new_conn()
        if not _is_public(sock.getpeername()[0]):
            sock.close()
            raise PrivateAddressRefused(self, self.host)
        return sock


class _PublicHTTPConnection(_PublicPeerOnly, HTTPConnection):
    pass


class _PublicHTTPSConnection(_PublicPeerOnly, HTTPSConnection):
    pass


class _PublicHTTPConnectionPool(HTTPConnectionPool):
    ConnectionCls = _PublicHTTPConnection


class _PublicHTTPSConnectionPool(HTTPSConnectionPool):
    ConnectionCls = _PublicHTTPSConnection


class PublicAddressAdapter(HTTPAdapter):
    """Connects only to addresses routable on the public internet."""

    def init_poolmanager(self, *args, **kwargs):
        super().init_poolmanager(*args, **kwargs)
        self.poolmanager.pool_classes_by_scheme = {
            "http": _PublicHTTPConnectionPool,
            "https": _PublicHTTPSConnectionPool,
        }
