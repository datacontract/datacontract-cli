import os
import re
from threading import Lock
from urllib.parse import urlparse

import requests

from datacontract.model.run import Run

# used to retrieve the HTML location of the published data contract or test results
RESPONSE_HEADER_LOCATION_HTML = "location-html"

# Pattern for a user-facing semantic definition URL exposed by the platform:
#   <scheme>://<host>/<vanity>/semantics/<namespace>/<externalId>
# These URLs appear in ODCS as `authoritativeDefinitions[type=semantics]`.
_SEMANTIC_URL_RE = re.compile(
    r"^(?P<scheme>https?)://(?P<host>[^/]+)/"
    r"(?P<vanity>[^/]+)/semantics/"
    r"(?P<namespace>[^/]+)/(?P<external_id>[^/?#]+)(?:[?#].*)?$"
)

# Per-process cache for resolved concepts. Keyed by the original URL so
# callers don't need to know whether resolution was successful.
_SEMANTIC_CACHE: dict[str, dict | None] = {}
_SEMANTIC_CACHE_LOCK = Lock()
_SEMANTIC_RESOLVE_TIMEOUT = 10  # seconds


def publish_test_results_to_entropy_data(run: Run, publish_url: str, ssl_verification: bool) -> bool:
    """Publish `run` to the Entropy Data instance. Returns True on success, False otherwise."""
    try:
        host = publish_url
        if publish_url is None:
            # this url supports Data Mesh Manager and Data Contract Manager
            host = _get_host()
            url = "%s/api/test-results" % host
        else:
            url = publish_url

        api_key = _get_api_key()

        if run.dataContractId is None:
            raise Exception("Cannot publish run results for unknown data contract ID")

        headers = {"Content-Type": "application/json", "x-api-key": api_key}
        request_body = run.model_dump_json()
        # print("Request Body:", request_body)
        response = requests.post(
            url,
            data=request_body,
            headers=headers,
            verify=ssl_verification,
        )
        # print("Status Code:", response.status_code)
        # print("Response Body:", response.text)
        if response.status_code != 200:
            display_host = _extract_hostname(host)
            run.log_error(f"Error publishing test results to {display_host}: {response.text}")
            return False
        run.log_info("Published test results successfully")

        location_html = response.headers.get(RESPONSE_HEADER_LOCATION_HTML)
        if location_html is not None and len(location_html) > 0:
            print(f"🚀 Open {location_html}")
        return True

    except Exception as e:
        run.log_error(f"Failed publishing test results. Error: {str(e)}")
        return False


def publish_data_contract_to_entropy_data(data_contract_dict: dict, ssl_verification: bool):
    try:
        api_key = _get_api_key()
        host = _get_host()
        headers = {"Content-Type": "application/json", "x-api-key": api_key}
        id = data_contract_dict["id"]
        url = f"{host}/api/datacontracts/{id}"
        response = requests.put(
            url=url,
            json=data_contract_dict,
            headers=headers,
            verify=ssl_verification,
        )
        if response.status_code != 200:
            display_host = _extract_hostname(host)
            print(f"Error publishing data contract to {display_host}: {response.text}")
            exit(1)

        print("✅ Published data contract successfully")

        location_html = response.headers.get(RESPONSE_HEADER_LOCATION_HTML)
        if location_html is not None and len(location_html) > 0:
            print(f"🚀 Open {location_html}")

    except Exception as e:
        print(f"Failed publishing data contract. Error: {str(e)}")


def _get_api_key() -> str:
    """
    Get API key from environment variables with fallback priority:
    1. ENTROPY_DATA_API_KEY
    2. DATAMESH_MANAGER_API_KEY
    3. DATACONTRACT_MANAGER_API_KEY
    """
    api_key = os.getenv("ENTROPY_DATA_API_KEY")
    if api_key is None:
        api_key = os.getenv("DATAMESH_MANAGER_API_KEY")
    if api_key is None:
        api_key = os.getenv("DATACONTRACT_MANAGER_API_KEY")
    if api_key is None:
        raise Exception(
            "Cannot publish, as neither ENTROPY_DATA_API_KEY, DATAMESH_MANAGER_API_KEY, nor DATACONTRACT_MANAGER_API_KEY is set"
        )
    return api_key


def _get_host() -> str:
    """
    Get host from environment variables with fallback priority:
    1. ENTROPY_DATA_HOST
    2. DATAMESH_MANAGER_HOST
    3. DATACONTRACT_MANAGER_HOST
    4. Default: https://api.entropy-data.com
    """
    host = os.getenv("ENTROPY_DATA_HOST")
    if host is None:
        host = os.getenv("DATAMESH_MANAGER_HOST")
    if host is None:
        host = os.getenv("DATACONTRACT_MANAGER_HOST")
    if host is None:
        host = "https://api.entropy-data.com"
    return host


def _extract_hostname(url: str) -> str:
    """
    Extract the hostname (including subdomains and top-level domain) from a URL.

    Examples:
    - https://app.entropy-data.com/path -> app.entropy-data.com
    - http://api.example.com:8080/api -> api.example.com
    """
    parsed = urlparse(url)
    return parsed.netloc.split(":")[0] if parsed.netloc else url


def _looks_like_entropy_data_host(host: str) -> bool:
    """True if `host` is a known/configured entropy-data host.

    Used to decide whether to attach the API key when resolving a URL
    named by a contract author. We never leak the key to arbitrary hosts.
    Matches the configured ENTROPY_DATA_HOST (or its aliases) and any
    `*.entropy-data.com` / `entropy-data.com` host.
    """
    if not host:
        return False
    host = host.lower().split(":")[0]
    if host == "entropy-data.com" or host.endswith(".entropy-data.com"):
        return True
    configured = (
        os.getenv("ENTROPY_DATA_HOST") or os.getenv("DATAMESH_MANAGER_HOST") or os.getenv("DATACONTRACT_MANAGER_HOST")
    )
    if configured:
        netloc = urlparse(configured).netloc.lower().split(":")[0]
        if netloc and host == netloc:
            return True
    return False


def _semantic_url_to_api(url: str) -> str | None:
    """Translate a user-facing semantic URL into the API endpoint.

    Input:  <scheme>://<host>/<vanity>/semantics/<namespace>/<externalId>
    Output: <scheme>://<host>/api/semantics/experimental
                /namespaces/<namespace>/concepts/<externalId>

    The vanity URL is not part of the API path — tenancy is resolved by
    the API key. Returns None if the URL doesn't match the expected shape.
    """
    m = _SEMANTIC_URL_RE.match(url or "")
    if not m:
        return None
    return (
        f"{m.group('scheme')}://{m.group('host')}/api/semantics/experimental"
        f"/namespaces/{m.group('namespace')}/concepts/{m.group('external_id')}"
    )


def resolve_semantic_definition(url: str, *, ssl_verification: bool = True) -> dict | None:
    """Resolve a semantic-definition URL to its concept document.

    `authoritativeDefinitions[type=semantics]` URLs in ODCS point at a
    concept maintained by the platform. Readers that need fields the
    contract doesn't inline (`logicalType`, `description`, ...) can call
    this to fetch the concept JSON; callers then merge selected fields
    into their in-memory model. The contract on disk is never mutated.

    Returns the concept dict on success, None on any failure (unknown URL
    shape, untrusted host that returned non-200, network error, malformed
    response). Results — including resolved None — are cached per-process
    by the original URL, so calling this once per property is cheap.

    The API key is only attached when the URL's host matches a known
    entropy-data host (or one configured via ENTROPY_DATA_HOST and its
    aliases). For other hosts the request goes anonymously, so a contract
    that names a third-party URL never receives the user's key.
    """
    if not url:
        return None
    with _SEMANTIC_CACHE_LOCK:
        if url in _SEMANTIC_CACHE:
            return _SEMANTIC_CACHE[url]
    api_url = _semantic_url_to_api(url)
    if api_url is None:
        with _SEMANTIC_CACHE_LOCK:
            _SEMANTIC_CACHE[url] = None
        return None

    headers = {"Accept": "application/json"}
    host = urlparse(api_url).netloc.split(":")[0]
    if _looks_like_entropy_data_host(host):
        try:
            headers["x-api-key"] = _get_api_key()
        except Exception:
            # No API key configured — attempt anonymously; if the endpoint
            # needs auth it will 401 and we return None below.
            pass

    try:
        response = requests.get(api_url, headers=headers, verify=ssl_verification, timeout=_SEMANTIC_RESOLVE_TIMEOUT)
    except requests.RequestException:
        with _SEMANTIC_CACHE_LOCK:
            _SEMANTIC_CACHE[url] = None
        return None

    if response.status_code != 200:
        with _SEMANTIC_CACHE_LOCK:
            _SEMANTIC_CACHE[url] = None
        return None

    try:
        concept = response.json()
    except ValueError:
        concept = None
    with _SEMANTIC_CACHE_LOCK:
        _SEMANTIC_CACHE[url] = concept
    return concept


def clear_semantic_cache() -> None:
    """Drop the per-process semantic-definition cache. Used by tests."""
    with _SEMANTIC_CACHE_LOCK:
        _SEMANTIC_CACHE.clear()
