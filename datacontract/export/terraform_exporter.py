import re
from typing import Optional

from open_data_contract_standard.model import OpenDataContractStandard, Server

from datacontract.export.exporter import Exporter


class TerraformExporter(Exporter):
    def export(self, data_contract, schema_name, server, sql_server_type, export_args) -> dict:
        return to_terraform(data_contract)


def _get_server_by_name(data_contract: OpenDataContractStandard, name: str) -> Optional[Server]:
    """Get a server by name."""
    if data_contract.servers is None:
        return None
    return next((s for s in data_contract.servers if s.server == name), None)


def to_terraform(data_contract: OpenDataContractStandard, server_id: str = None) -> str:
    if data_contract is None:
        return ""
    if data_contract.servers is None or len(data_contract.servers) == 0:
        return ""

    result = ""
    for server in data_contract.servers:
        server_name = server.server
        if server_id is not None and server_name != server_id:
            continue
        result = server_to_terraform_resource(data_contract, result, server, server_name)

    return result.strip()


def _get_server_custom_property(server: Server, key: str) -> Optional[str]:
    """Get a custom property from the server."""
    if server.customProperties is None:
        return None
    for cp in server.customProperties:
        if cp.property == key:
            return cp.value
    return None


def server_to_terraform_resource(data_contract: OpenDataContractStandard, result, server: Server, server_name):
    tag_data_contract = data_contract.id
    tag_name = data_contract.name
    tag_server = server_name
    bucket_name = extract_bucket_name(server)
    resource_id = f"{data_contract.id}_{server_name}"
    # Get dataProductId from data_contract or server customProperties
    data_product_id = data_contract.dataProduct or _get_server_custom_property(server, "dataProductId")

    if data_product_id is not None:
        result += f"""
resource "aws_s3_bucket" "{resource_id}" {{
  bucket = "{bucket_name}"

  tags = {{
    Name         = "{tag_name}"
    DataContract = "{tag_data_contract}"
    Server       = "{tag_server}"
    DataProduct  = "{data_product_id}"
  }}
}}

"""
    else:
        result += f"""
resource "aws_s3_bucket" "{resource_id}" {{
  bucket = "{bucket_name}"

  tags = {{
    Name         = "{tag_name}"
    DataContract = "{tag_data_contract}"
    Server       = "{tag_server}"
  }}
}}

"""
    return result


def extract_bucket_name(server) -> str | None:
    if server.type == "s3":
        s3_url = server.location
        # Regular expression to match the S3 bucket name
        match = re.search(r"s3://([^/]+)/", s3_url)
        if match:
            # Return the first group (bucket name)
            return match.group(1)
        else:
            return ""

    return ""
