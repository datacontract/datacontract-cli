import re

from datacontract.model.data_contract_specification import DataContractSpecification, Server
from datacontract.export.exporter import Exporter


class TerraformExporter(Exporter):
    def export(self, data_contract, model, server, sql_server_type, export_args) -> dict:
        return to_terraform(data_contract)


def to_terraform(data_contract_spec: DataContractSpecification, server_id: str = None) -> str:
    if data_contract_spec is None:
        return ""
    if data_contract_spec.servers is None or len(data_contract_spec.servers) == 0:
        return ""

    result = ""
    for server_name, server in iter(data_contract_spec.servers.items()):
        if server_id is not None and server_name != server_id:
            continue
        result = server_to_terraform_resource(data_contract_spec, result, server, server_name)

    return result.strip()


def server_to_terraform_resource(data_contract_spec, result, server: Server, server_name):
    tag_data_contract = data_contract_spec.id
    tag_name = data_contract_spec.info.title
    tag_server = server_name
    bucket_name = extract_bucket_name(server)
    resource_id = f"{data_contract_spec.id}_{server_name}"
    data_product_id = server.dataProductId

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
