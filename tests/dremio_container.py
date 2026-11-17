"""A Dremio OSS container for the tests that test and import against Dremio."""

import logging
import time
from pathlib import Path

import requests
from testcontainers.core.container import DockerContainer

from datacontract.engines.ibis.connections.dremio import DremioRestClient

log = logging.getLogger(__name__)

USERNAME = "admin"
PASSWORD = "Admin123!"


class DremioContainer(DockerContainer):
    """Dremio OSS with one admin user, reached through the REST API of its web console."""

    def __init__(self, image: str = "dremio/dremio-oss:26.0.5", **kwargs) -> None:
        super().__init__(image, **kwargs)
        self.with_exposed_ports(9047)

    def start(self, timeout: int = 240) -> "DremioContainer":
        super().start()
        start = time.time()
        while True:
            try:
                if requests.get(f"{self.url()}/apiv2/server_status", timeout=5).ok:
                    break
            except requests.RequestException as e:
                log.debug(e)
            if time.time() - start > timeout:
                raise TimeoutError(f"Dremio did not start within {timeout} seconds")
            time.sleep(2)
        # A fresh Dremio has no user; the first one is created without signing in.
        requests.put(
            f"{self.url()}/apiv2/bootstrap/firstuser",
            headers={"Authorization": "_dremionull"},
            json={
                "userName": USERNAME,
                "firstName": "Ada",
                "lastName": "Admin",
                "email": "admin@example.com",
                "password": PASSWORD,
            },
            timeout=30,
        ).raise_for_status()
        return self

    def port(self) -> int:
        return int(self.get_exposed_port(9047))

    def url(self) -> str:
        return f"http://{self.get_container_host_ip()}:{self.port()}"

    def client(self) -> DremioRestClient:
        return DremioRestClient(self.url(), username=USERNAME, password=PASSWORD)

    def create_folders(self, *paths: list[str]) -> None:
        """Creates a space (a path of one name) or a folder in a space, parents first."""
        for path in paths:
            body = (
                {"entityType": "space", "name": path[0]} if len(path) == 1 else {"entityType": "folder", "path": path}
            )
            requests.post(
                f"{self.url()}/api/v3/catalog",
                json=body,
                headers={"Authorization": self.client().authorization()},
                timeout=30,
            ).raise_for_status()

    def load(self, folder: str, data_file: str) -> str:
        """Creates the orders table in a folder of the file system source $scratch, which nests folders."""
        client = self.client()
        with open(Path(__file__).parent / "fixtures/dremio/data" / data_file) as file:
            statement = "\n".join(line for line in file.read().splitlines() if not line.strip().startswith("--"))
        client.run(statement.replace("__TABLE__", f"{folder}.orders"))
        # A table in a nested folder of a file system source only shows in INFORMATION_SCHEMA once its metadata is read.
        client.run(f"ALTER TABLE {folder}.orders REFRESH METADATA")
        return folder
