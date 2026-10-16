"""Requests to the HTTP APIs that `api` servers and OData services name."""

import ipaddress

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


class _PublicPeerOnly:
    # Checks the address actually connected to, before anything is sent, so DNS rebinding cannot get around it.
    def _new_conn(self):
        sock = super()._new_conn()
        address = ipaddress.ip_address(sock.getpeername()[0])
        if not (getattr(address, "ipv4_mapped", None) or address).is_global:
            sock.close()
            raise NewConnectionError(
                self,
                f"Refused to connect to {address}: a posted data contract may not reach a private network address. "
                f"Start the API server with --allow-private-network to allow it.",
            )
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
