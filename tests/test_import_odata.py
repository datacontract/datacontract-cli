import json
import re
import traceback
from io import BytesIO
from pathlib import Path
from unittest.mock import Mock

import jsonschema
import pytest
import requests
import yaml
from typer.testing import CliRunner

from datacontract import Config
from datacontract.cli import app
from datacontract.config import set_cli_config
from datacontract.data_contract import DataContract
from datacontract.model.exceptions import DataContractException

ROOT = "https://xmart-api-public-uat.who.int/refmart/"
METADATA = "https://xmart-api-public-uat.who.int/refmart/$metadata"
FIXTURES = Path(__file__).parent / "fixtures/odata"
ODATA_VERSIONS = ["4.0", "4.01", "4.02", "4.1", "4.123"]


@pytest.fixture(autouse=True)
def isolate_authentication(monkeypatch):
    monkeypatch.delenv("DATACONTRACT_API_HEADER_AUTHORIZATION", raising=False)
    set_cli_config(None)
    yield
    set_cli_config(None)


@pytest.fixture
def metadata_response(monkeypatch):
    response = Mock()
    response.content = (FIXTURES / "who-metadata.xml").read_bytes()
    response.headers = {"OData-Version": "4.0"}
    get = Mock(return_value=response)
    monkeypatch.setattr("datacontract.imports.odata_importer._ODataSession.get", get)
    return response, get


def import_contract(entity_set="ref_country", *, source=ROOT, **kwargs):
    return DataContract.import_from_source(
        "odata", source=source, odata_entity_set=[entity_set], odata_metadata_url=METADATA, **kwargs
    )


def metadata_xml(properties="", *, version="4.01", entity_attributes="", extra_schema="", extra_sets="", keys=""):
    return f'''<edmx:Edmx xmlns:edmx="http://docs.oasis-open.org/odata/ns/edmx" Version="{version}">
      <edmx:DataServices>
        <Schema xmlns="http://docs.oasis-open.org/odata/ns/edm" Namespace="Demo" Alias="D">
          <EntityType Name="Country" {entity_attributes}>{keys}{properties}</EntityType>
          <EntityContainer Name="Service">
            <EntitySet Name="REF_COUNTRY" EntityType="D.Country" />{extra_sets}
          </EntityContainer>{extra_schema}
        </Schema>
      </edmx:DataServices>
    </edmx:Edmx>'''.encode()


def test_who_contract_and_transport(metadata_response):
    response, get = metadata_response
    contract = import_contract()
    actual = yaml.safe_load(contract.to_yaml())
    assert actual == yaml.safe_load((FIXTURES / "who-contract.yaml").read_text())
    schema = json.loads((Path(__file__).parents[1] / "datacontract/schemas/odcs-3.2.0.schema.json").read_text())
    jsonschema.validate(actual, schema)
    get.assert_called_once()
    assert get.call_args.args == (METADATA,)
    assert get.call_args.kwargs["headers"] == {
        "Accept": "application/xml, application/json;q=0.9",
    }
    assert get.call_args.kwargs["timeout"] == 30
    response.raise_for_status.assert_called_once()
    # The explicit auth handler must prevent implicit .netrc credentials.
    request = requests.Request("GET", METADATA).prepare()
    assert get.call_args.kwargs["auth"](request).headers.get("Authorization") is None


@pytest.mark.parametrize("version", ODATA_VERSIONS)
@pytest.mark.parametrize("header", [True, False])
def test_versions_and_header_fallback(metadata_response, version, header):
    response, _ = metadata_response
    response.content = metadata_xml('<Property Name="Code" Type="Edm.String" />', version=version)
    response.headers = {"OData-Version": version} if header else {}
    contract = import_contract()
    assert contract.servers[0].customProperties[1].value == version
    assert contract.schema_[0].properties[0].name == "Code"


@pytest.mark.parametrize(
    "edm_type, logical_type",
    [
        ("String", "string"),
        ("Guid", "string"),
        ("Byte", "integer"),
        ("SByte", "integer"),
        ("Int16", "integer"),
        ("Int32", "integer"),
        ("Int64", "integer"),
        ("Decimal", "number"),
        ("Single", "number"),
        ("Double", "number"),
        ("Boolean", "boolean"),
        ("Date", "date"),
        ("DateTimeOffset", "timestamp"),
        ("TimeOfDay", "time"),
    ],
)
@pytest.mark.parametrize("format", ["xml", "json"])
def test_primitive_types(metadata_response, edm_type, logical_type, format):
    response, _ = metadata_response
    response.headers = {}
    if format == "xml":
        response.content = metadata_xml(f'<Property Name="Value" Type="Edm.{edm_type}" />')
        prop = import_contract().schema_[0].properties[0]
    else:
        document = json.loads((FIXTURES / "products.json").read_text())
        document["Catalog.Model"]["Product"] = {
            "$Kind": "EntityType",
            "Value": {"$Type": f"Edm.{edm_type}", "$Nullable": True},
        }
        response.content = json.dumps(document).encode()
        prop = import_contract("Products").schema_[0].properties[0]
    assert prop.logicalType == logical_type
    assert prop.physicalType == f"Edm.{edm_type}"
    assert prop.required is False
    if edm_type == "Guid":
        assert prop.logicalTypeOptions == {"format": "uuid"}
    facets = {p.property: p.value for p in prop.customProperties or []}
    if edm_type == "Decimal":
        assert facets == {"scale": 0 if format == "xml" else "variable"}
    else:
        assert "scale" not in facets


def test_keys_nullability_and_facets(metadata_response):
    response, _ = metadata_response
    response.headers = {}
    response.content = metadata_xml(
        """<Property Name="Code" Type="Edm.String" Nullable="false" MaxLength="3" />
        <Property Name="Year" Type="Edm.Int32" Nullable="false" />
        <Property Name="Amount" Type="Edm.Decimal" Precision="12" Scale="2" Nullable="true" />
        <Property Name="Variable" Type="Edm.Decimal" Scale="variable" />
        <Property Name="Floating" Type="Edm.Decimal" Scale="floating" />
        <Property Name="Text" Type="Edm.String" MaxLength="max" />""",
        keys='<Key><PropertyRef Name="Year" /><PropertyRef Name="Code" /></Key>',
    )
    code, year, amount, variable, floating, text = import_contract().schema_[0].properties
    assert code.required is True and year.required is True
    assert code.primaryKey is True and year.primaryKey is True
    assert (code.primaryKeyPosition, year.primaryKeyPosition) == (2, 1)
    assert not code.unique and not year.unique
    assert code.logicalTypeOptions == {"maxLength": 3}
    assert amount.required is False and not amount.primaryKey
    assert {p.property: p.value for p in amount.customProperties} == {"precision": 12, "scale": 2}
    assert variable.customProperties[0].value == "variable"
    assert floating.customProperties[0].value == "floating"
    assert not text.logicalTypeOptions


@pytest.mark.parametrize("entity_set", ["REF_COUNTRY", "ref_country", "Ref_Country"])
@pytest.mark.parametrize("root", ["https://example.com", "https://example.com/service", "https://example.com/service/"])
def test_entity_set_matching_normalizes_root(metadata_response, entity_set, root):
    contract = import_contract(entity_set, source=root)
    assert contract.schema_[0].name == "REF_COUNTRY"
    assert contract.servers[0].location == root.rstrip("/") + "/"
    assert {p.property: p.value for p in contract.schema_[0].customProperties} == {
        "odataEntitySet": "REF_COUNTRY",
        "odataEntitySetUrl": root.rstrip("/") + "/REF_COUNTRY",
    }


def test_exact_match_wins_and_casefold_ambiguity_fails(metadata_response):
    response, _ = metadata_response
    response.headers = {}
    response.content = metadata_xml(extra_sets='<EntitySet Name="ref_country" EntityType="Demo.Country" />')
    assert import_contract().schema_[0].name == "ref_country"
    with pytest.raises(DataContractException, match="ambiguous"):
        import_contract("Ref_Country")


def test_navigation_and_unrelated_types_are_omitted(metadata_response, caplog):
    response, _ = metadata_response
    response.headers = {}
    response.content = metadata_xml(
        '<Property Name="Code" Type="Edm.String" /><NavigationProperty Name="Related" Type="Collection(D.Country)" />',
        extra_schema='<ComplexType Name="Unused"><Property Name="Nested" Type="Collection(Edm.String)" /></ComplexType>',
    )
    contract = import_contract()
    assert [p.name for p in contract.schema_[0].properties] == ["Code"]
    assert "Omitting OData navigation property REF_COUNTRY.Related" in caplog.text


@pytest.mark.parametrize(
    "field_type",
    ["D.Address", "Collection(Edm.String)", "Collection(D.Address)", "D.Status", "Edm.Binary", "Edm.Unknown"],
)
def test_unsupported_types_fail_with_field_and_type(metadata_response, field_type):
    response, _ = metadata_response
    response.headers = {}
    response.content = metadata_xml(f'<Property Name="Value" Type="{field_type}" />')
    with pytest.raises(DataContractException) as error:
        import_contract()
    assert "REF_COUNTRY.Value" in str(error.value)
    assert field_type in str(error.value)


@pytest.mark.parametrize(
    "document, header, error",
    [
        (metadata_xml(version="3.0"), "3.0", "Unsupported OData version"),
        (metadata_xml(version="5.0"), "5.0", "Unsupported OData version"),
        (metadata_xml(version="4.0"), "4.01", "Conflicting OData versions"),
        (metadata_xml(entity_attributes='BaseType="Demo.Base"'), None, "inheritance"),
        (metadata_xml().replace(b'Name="Service"', b'Name="Service" Extends="Demo.Base"'), None, "inheritance"),
        (metadata_xml().replace(b"D.Country", b"Other.Country"), None, "must resolve uniquely"),
        (metadata_xml().replace(b"REF_COUNTRY", b"OTHER"), None, "not found"),
        (metadata_xml().replace(b'http://docs.oasis-open.org/odata/ns/edm"', b'urn:wrong"'), None, "not found"),
        (b"<html />", None, "Expected an OData 4 Edmx"),
        (b"<broken", None, "Invalid or unsafe"),
        (metadata_xml('<Property Name="P" Type="Edm.String" Nullable="maybe" />'), None, "Invalid Nullable"),
        (metadata_xml('<Property Name="P" Type="Edm.String" MaxLength="bad" />'), None, "Invalid MaxLength"),
        (metadata_xml(keys='<Key><PropertyRef Name="Missing" /></Key>'), None, "key references"),
    ],
)
def test_metadata_errors(metadata_response, document, header, error):
    response, _ = metadata_response
    response.content = document
    response.headers = {"OData-Version": header} if header else {}
    with pytest.raises(DataContractException, match=error):
        import_contract()


@pytest.mark.parametrize("encoding", ["utf-8", "utf-16"])
@pytest.mark.parametrize(
    "doctype",
    [
        "<!DOCTYPE edmx:Edmx>",
        '<!DOCTYPE edmx:Edmx [<!ENTITY country "REF_COUNTRY">]>',
        '<!DOCTYPE edmx:Edmx [<!ENTITY country SYSTEM "file:///etc/passwd">]>',
        '<!DOCTYPE edmx:Edmx SYSTEM "https://example.com/metadata.dtd">',
    ],
)
def test_metadata_rejects_dtd(metadata_response, encoding, doctype):
    response, _ = metadata_response
    response.headers = {}
    document = metadata_xml().decode().replace('Name="REF_COUNTRY"', 'Name="&country;"')
    response.content = (f'<?xml version="1.0" encoding="{encoding}"?>{doctype}{document}').encode(encoding)
    with pytest.raises(DataContractException, match="DTD declarations are not allowed"):
        import_contract()


@pytest.mark.parametrize("encoding", ["utf-8", "utf-16"])
def test_metadata_encoding_and_escaped_text(metadata_response, encoding):
    response, _ = metadata_response
    response.headers = {}
    document = metadata_xml('<Property Name="Code" Type="Edm.String" DefaultValue="A &amp; B" />').decode()
    response.content = (
        f'<?xml version="1.0" encoding="{encoding}"?><!-- literal <!DOCTYPE is harmless here -->{document}'
    ).encode(encoding)
    assert import_contract().schema_[0].properties[0].name == "Code"


@pytest.mark.parametrize(
    "location",
    [
        None,
        "",
        "file:///tmp/source",
        "https://example.com:bad/",
        ROOT + "?$select=CODE_ISO_3",
        ROOT + "#fragment",
        "https://user:secret@example.com/Countries",
    ],
)
def test_invalid_root_does_not_fetch_metadata(metadata_response, location):
    _, get = metadata_response
    with pytest.raises(DataContractException, match="Invalid service-root-url"):
        import_contract(source=location)
    get.assert_not_called()


@pytest.mark.parametrize(
    "options",
    [{"odata_metadata_url": METADATA, "odata_metadata_file": FIXTURES / "who-metadata.xml"}],
)
def test_metadata_sources_are_mutually_exclusive_for_python_api(metadata_response, options):
    _, get = metadata_response
    with pytest.raises(DataContractException, match="mutually exclusive"):
        DataContract.import_from_source("odata", source=ROOT, odata_entity_set=["ref_country"], **options)
    get.assert_not_called()


@pytest.mark.parametrize("error", [requests.Timeout("timed out"), requests.ConnectionError("connection failed")])
def test_network_errors(metadata_response, error):
    _, get = metadata_response
    get.side_effect = error
    with pytest.raises(DataContractException, match="Failed to fetch OData metadata") as exc:
        import_contract()
    assert exc.value.type == "connection"


@pytest.mark.parametrize("status", [401, 403, 404, 500])
def test_http_errors(metadata_response, status):
    response, _ = metadata_response
    response.status_code = status
    response.raise_for_status.side_effect = requests.HTTPError(f"HTTP {status}", response=response)
    with pytest.raises(DataContractException, match=f"HTTP {status}"):
        import_contract()


def test_cli_stdout_and_output(metadata_response, tmp_path):
    runner = CliRunner()
    args = ["import", "odata", "--service-root-url", ROOT, "--entity-set", "ref_country", "--metadata-url", METADATA]
    stdout = runner.invoke(app, args)
    assert stdout.exit_code == 0, stdout.output
    assert yaml.safe_load(stdout.stdout) == yaml.safe_load((FIXTURES / "who-contract.yaml").read_text())
    output = tmp_path / "contract.yaml"
    result = runner.invoke(app, args + ["--output", str(output), "--owner", "WHO", "--id", "country", "--debug"])
    assert result.exit_code == 0, result.output
    contract = yaml.safe_load(output.read_text())
    assert contract["id"] == "country"
    assert contract["team"]["name"] == "WHO"


@pytest.mark.parametrize(
    "args",
    [
        [],
        ["--metadata-url", METADATA],
        ["--metadata-file", str(FIXTURES / "who-metadata.xml")],
        ["--service-root-url", ROOT, "--entity-set", "ref_country", "--metadataUrl", METADATA],
        [
            "--service-root-url",
            ROOT,
            "--entity-set",
            "ref_country",
            "--metadata-url",
            METADATA,
            "--metadata-file",
            str(FIXTURES / "who-metadata.xml"),
        ],
    ],
)
def test_cli_requires_options_and_rejects_alias(metadata_response, args):
    _, get = metadata_response
    result = CliRunner().invoke(app, ["import", "odata"] + args)
    assert result.exit_code == 2
    get.assert_not_called()


def test_failed_import_preserves_existing_output(metadata_response, tmp_path):
    response, _ = metadata_response
    response.content = b"invalid XML"
    output = tmp_path / "contract.yaml"
    output.write_text("existing contract")
    result = CliRunner().invoke(
        app,
        [
            "import",
            "odata",
            "--service-root-url",
            ROOT,
            "--entity-set",
            "ref_country",
            "--metadata-url",
            METADATA,
            "--output",
            str(output),
        ],
    )
    assert result.exit_code != 0
    assert output.read_text() == "existing contract"


@pytest.mark.parametrize("path_type", [str, Path])
def test_local_who_metadata_matches_url_import(metadata_response, path_type):
    _, get = metadata_response
    path = path_type(FIXTURES / "who-metadata.xml")
    contract = DataContract.import_from_source(
        "odata", source=ROOT, odata_entity_set=["ref_country"], odata_metadata_file=path
    )
    actual = yaml.safe_load(contract.to_yaml())
    expected = yaml.safe_load((FIXTURES / "who-contract.yaml").read_text())
    expected["servers"][0]["customProperties"][2] = {"property": "odataMetadataFile", "value": str(path)}
    assert actual == expected
    get.assert_not_called()


@pytest.mark.parametrize("version", ODATA_VERSIONS)
@pytest.mark.parametrize("encoding", ["utf-8", "utf-16"])
def test_local_metadata_version_and_encoding(metadata_response, tmp_path, version, encoding):
    _, get = metadata_response
    path = tmp_path / "metadata.xml"
    document = metadata_xml('<Property Name="Code" Type="Edm.String" />', version=version).decode()
    path.write_bytes((f'<?xml version="1.0" encoding="{encoding}"?>{document}').encode(encoding))
    contract = DataContract.import_from_source(
        "odata", source=ROOT, odata_entity_set=["ref_country"], odata_metadata_file=path
    )
    assert contract.servers[0].customProperties[1].value == version
    assert contract.schema_[0].properties[0].name == "Code"
    get.assert_not_called()


@pytest.mark.parametrize("kind", ["missing", "directory", "unreadable", "malformed", "dtd"])
def test_local_metadata_errors_preserve_output(metadata_response, tmp_path, monkeypatch, kind):
    _, get = metadata_response
    path = tmp_path / "metadata.xml"
    if kind == "directory":
        path.mkdir()
    elif kind == "unreadable":
        monkeypatch.setattr(Path, "read_bytes", Mock(side_effect=PermissionError("Permission denied")))
    elif kind == "malformed":
        path.write_bytes(b"not XML")
    elif kind == "dtd":
        path.write_bytes(b'<!DOCTYPE edmx:Edmx [<!ENTITY name "Country">]>' + metadata_xml())
    output = tmp_path / "contract.yaml"
    output.write_text("existing contract")
    result = CliRunner().invoke(
        app,
        [
            "import",
            "odata",
            "--service-root-url",
            ROOT,
            "--entity-set",
            "ref_country",
            "--metadata-file",
            str(path),
            "--output",
            str(output),
        ],
    )
    assert result.exit_code != 0
    assert isinstance(result.exception, DataContractException)
    message = "Invalid or unsafe" if kind in ("malformed", "dtd") else "Failed to read OData metadata file"
    assert message in str(result.exception)
    assert output.read_text() == "existing contract"
    get.assert_not_called()


SERVICE_ROOT = "https://example.com/odata/"


@pytest.fixture
def json_metadata(metadata_response):
    response, _ = metadata_response
    response.headers = {}
    return json.loads((FIXTURES / "products.json").read_text())


@pytest.mark.parametrize("source", ["file", "url"])
@pytest.mark.parametrize("version", ODATA_VERSIONS)
@pytest.mark.parametrize("scale", [None, 0, 2])
def test_xml_json_equivalent_contracts(metadata_response, tmp_path, source, version, scale):
    response, get = metadata_response
    response.headers = {"OData-Version": version, "Content-Type": "text/plain"}
    contracts = []
    for format in ("xml", "json"):
        content = (FIXTURES / f"products.{format}").read_bytes().replace(b"4.01", version.encode())
        if format == "xml":
            content = content.replace(b' Scale="2"', b"" if scale is None else f' Scale="{scale}"'.encode(), 1)
        else:
            document = json.loads(content)
            document["Catalog.Model"]["Product"]["Price"]["$Scale"] = 0 if scale is None else scale
            content = json.dumps(document).encode()
        if source == "file":
            # Deliberately use an unrelated extension: content determines the format.
            path = tmp_path / "metadata.txt"
            path.write_bytes(content)
            contract = DataContract.import_from_source(
                "odata", source=SERVICE_ROOT, odata_entity_set=["Products"], odata_metadata_file=path
            )
            get.assert_not_called()
        else:
            response.content = content
            contract = import_contract("Products", source=SERVICE_ROOT)
        actual = yaml.safe_load(contract.to_yaml())
        schema = json.loads((Path(__file__).parents[1] / "datacontract/schemas/odcs-3.2.0.schema.json").read_text())
        jsonschema.validate(actual, schema)
        contracts.append(actual)
    assert contracts[0] == contracts[1]
    properties = contracts[0]["schema"][0]["properties"]
    assert [p["name"] for p in properties] == [
        "Sku",
        "Revision",
        "Price",
        "PublishedAt",
        "Active",
        "TrackingId",
        "Description",
    ]
    assert [p["primaryKeyPosition"] for p in properties[:2]] == [2, 1]
    assert not any(p.get("unique") for p in properties)
    assert properties[0]["required"] and not properties[2]["required"]
    assert properties[0]["logicalTypeOptions"] == {"maxLength": 32}
    assert properties[2]["customProperties"] == [
        {"property": "precision", "value": 10},
        {"property": "scale", "value": 0 if scale is None else scale},
    ]


@pytest.mark.parametrize("format", ["xml", "json"])
def test_cli_synthetic_metadata_file(metadata_response, tmp_path, monkeypatch, format):
    _, get = metadata_response
    content = (FIXTURES / f"products.{format}").read_bytes()
    monkeypatch.chdir(tmp_path)
    Path("metadata").write_bytes(content)
    args = [
        "import",
        "odata",
        "--service-root-url",
        SERVICE_ROOT,
        "--entity-set",
        "Products",
        "--metadata-file",
        "metadata",
        "--owner",
        "Catalog",
        "--id",
        "products",
    ]
    stdout = CliRunner().invoke(app, args)
    assert stdout.exit_code == 0, stdout.output
    actual = yaml.safe_load(stdout.stdout)
    assert actual["name"] == "Products"
    assert actual["id"] == "products" and actual["team"]["name"] == "Catalog"
    assert {"property": "odataMetadataFile", "value": "metadata"} in actual["servers"][0]["customProperties"]
    result = CliRunner().invoke(app, args + ["--output", "contract.yaml"])
    assert result.exit_code == 0, result.output
    assert yaml.safe_load(Path("contract.yaml").read_text()) == actual
    get.assert_not_called()


@pytest.mark.parametrize("source", ["file", "url"])
@pytest.mark.parametrize("encoding", ["utf-8", "utf-8-sig", "utf-16", "utf-32"])
def test_json_encoding_and_leading_whitespace(metadata_response, tmp_path, source, encoding):
    response, get = metadata_response
    content = (" \n\t" * 100 + (FIXTURES / "products.json").read_text()).encode(encoding)
    response.headers = {"Content-Type": "application/xml"}
    if source == "file":
        path = tmp_path / "metadata.xml"
        path.write_bytes(content)
        contract = DataContract.import_from_source(
            "odata", source=SERVICE_ROOT, odata_entity_set=["Products"], odata_metadata_file=path
        )
        get.assert_not_called()
    else:
        response.content = content
        result = CliRunner().invoke(
            app,
            [
                "import",
                "odata",
                "--service-root-url",
                SERVICE_ROOT,
                "--entity-set",
                "Products",
                "--metadata-url",
                METADATA,
            ],
        )
        assert result.exit_code == 0, result.output
        assert yaml.safe_load(result.stdout)["name"] == "Products"
        get.assert_called_once_with(METADATA, **get.call_args.kwargs)
        return
    assert contract.name == "Products"


def test_json_defaults_and_annotations(metadata_response, json_metadata):
    response, _ = metadata_response
    json_metadata["Catalog.Model"]["Product"] = {
        "$Kind": "EntityType",
        "Label": {},
        "Amount": {"$Type": "Edm.Decimal"},
        "Optional": {"$Kind": "Property", "$Nullable": True},
        "@Example.Note": "ignored",
        "Label@Example.Note": "also ignored",
    }
    response.content = json.dumps(json_metadata).encode()
    label, amount, optional = import_contract("Products").schema_[0].properties
    assert label.physicalType == "Edm.String" and label.required
    assert amount.required
    assert {p.property: p.value for p in amount.customProperties} == {"scale": "variable"}
    assert len(amount.customProperties) == 1  # No inferred precision.
    assert not optional.required
    assert not any(p.primaryKey for p in (label, amount, optional))


@pytest.mark.parametrize("type_name", ["Catalog.Product", "Catalog.Model.Product"])
def test_json_alias_and_navigation(metadata_response, json_metadata, caplog, type_name):
    response, get = metadata_response
    json_metadata["Catalog.Service"]["Store"]["Products"]["$Type"] = type_name
    json_metadata["Catalog.Model"]["Product"]["Orders"] = {
        "$Kind": "NavigationProperty",
        "$Type": "External.Order",
        "$Collection": True,
    }
    json_metadata["Catalog.Model"]["Unused"] = {"$Kind": "ComplexType", "Nested": {"$Type": "External.Unknown"}}
    json_metadata["$Reference"] = {"https://example.com/external/$metadata": {"$Include": [{"$Namespace": "External"}]}}
    json_metadata["Catalog.Service"]["Store"]["Featured"] = {"$Type": "Catalog.Product"}  # Singleton.
    response.content = json.dumps(json_metadata).encode()
    contract = import_contract("Products")
    assert len(contract.schema_[0].properties) == 7
    assert "Omitting OData navigation property Products.Orders" in caplog.text
    get.assert_called_once()


@pytest.mark.parametrize("entity_set", ["Products", "products", "PRODUCTS"])
def test_json_name_matching(metadata_response, json_metadata, entity_set):
    response, _ = metadata_response
    response.content = json.dumps(json_metadata).encode()
    contract = import_contract(entity_set, source=SERVICE_ROOT)
    assert contract.name == "Products" and contract.servers[0].location == SERVICE_ROOT


def test_json_exact_match_and_ambiguous_names(metadata_response, json_metadata):
    response, _ = metadata_response
    json_metadata["Catalog.Service"]["Store"]["products"] = {"$Collection": True, "$Type": "Catalog.Product"}
    response.content = json.dumps(json_metadata).encode()
    assert import_contract("Products").name == "Products"
    with pytest.raises(DataContractException, match="ambiguous"):
        import_contract("PRODUCTS")
    with pytest.raises(DataContractException, match="not found"):
        import_contract("Missing")


@pytest.mark.parametrize(
    "path,value,error",
    [
        (("$Version",), "3.0", "Unsupported OData version"),
        (("$Version",), 4.01, "Unsupported OData version"),
        (("$EntityContainer",), [], "namespace-qualified"),
        (("$EntityContainer",), "Missing.Store", "JSON object"),
        (("Catalog.Model", "$Alias"), 42, "Invalid .*Alias"),
        (("Catalog.Model", "$Alias"), None, "Invalid .*Alias"),
        (("Catalog.Service", "Store", "$Kind"), "EntityType", "EntityContainer"),
        (("Catalog.Service", "Store", "$Extends"), "Other.Store", "inheritance"),
        (("Catalog.Service", "Store", "Products", "$Collection"), "true", "Invalid .*Collection"),
        (("Catalog.Service", "Store", "Products", "$Collection"), False, "not found"),
        (("Catalog.Service", "Store", "Products", "$Type"), [], "qualified type name"),
        (("Catalog.Service", "Store", "Products", "$Type"), "External.Product", "External metadata references"),
        (("Catalog.Model", "Product", "$BaseType"), "Catalog.Base", "inheritance"),
        (("Catalog.Model", "Product", "$BaseType"), None, "Invalid .*BaseType"),
        (("Catalog.Model", "Product", "$Key"), "Sku", "key references"),
        (("Catalog.Model", "Product", "$Key"), ["Sku", "Sku"], "key references"),
        (("Catalog.Model", "Product", "$Key"), ["Missing"], "key references"),
        (("Catalog.Model", "Product", "$Key"), [{"Alias": "Address/Code"}], "key references"),
        (("Catalog.Model", "Product", "Sku", "$Nullable"), True, "Key field"),
        (("Catalog.Model", "Product", "Price"), [], "JSON object"),
        (("Catalog.Model", "Product", "Price", "$Kind"), "Unexpected", "Unsupported .*Kind"),
        (("Catalog.Model", "Product", "Price", "$Type"), None, "Unsupported OData type"),
        (("Catalog.Model", "Product", "Price", "$Nullable"), "false", "Invalid Nullable"),
        (("Catalog.Model", "Product", "Price", "$Collection"), 1, "Invalid .*Collection"),
        (("Catalog.Model", "Product", "Price", "$Collection"), True, "collection"),
        (("Catalog.Model", "Product", "Price", "$Precision"), "10", "Invalid Precision"),
        (("Catalog.Model", "Product", "Price", "$Scale"), True, "Invalid Scale"),
        (("Catalog.Model", "Product", "Sku", "$MaxLength"), -1, "Invalid MaxLength"),
        (("Catalog.Model", "Product", "Sku", "$MaxLength"), None, "Invalid MaxLength"),
    ],
)
def test_json_invalid_csdl(metadata_response, json_metadata, path, value, error):
    response, _ = metadata_response
    target = json_metadata
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    response.content = json.dumps(json_metadata).encode()
    with pytest.raises(DataContractException, match=error):
        import_contract("Products")


@pytest.mark.parametrize("kind", ["ComplexType", "EnumType", "TypeDefinition"])
def test_json_unsupported_selected_type(metadata_response, json_metadata, kind):
    response, _ = metadata_response
    json_metadata["Catalog.Model"]["Special"] = {"$Kind": kind}
    json_metadata["Catalog.Model"]["Product"]["Price"]["$Type"] = "Catalog.Special"
    response.content = json.dumps(json_metadata).encode()
    with pytest.raises(DataContractException, match="Catalog.Special.*Products.Price"):
        import_contract("Products")


@pytest.mark.parametrize(
    "content,error",
    [
        (b'{"$Version": "4.01",', "Invalid or unsafe"),
        (b'{"$Version":"4.01","$Version":"4.0"}', "Duplicate JSON key"),
        (b'{"Schema":{"Field":{},"Field":{}}}', "Duplicate JSON key"),
        (b'{"value":NaN}', "Invalid JSON constant"),
        (b'{"value":Infinity}', "Invalid JSON constant"),
        (b"[]", "JSON object"),
        (b"null", "JSON object"),
        (b'{"bad":"\xff"}', "Invalid or unsafe"),
        (
            b'{"@odata.context":"https://example.com/odata/$metadata","value":[{"name":"Products","kind":"EntitySet","url":"Products"}]}',
            "service/data document.*field definitions",
        ),
    ],
)
def test_json_invalid_documents_preserve_output(metadata_response, tmp_path, content, error):
    response, get = metadata_response
    response.headers = {}
    response.content = content
    output = tmp_path / "contract.yaml"
    result = CliRunner().invoke(
        app,
        [
            "import",
            "odata",
            "--service-root-url",
            SERVICE_ROOT,
            "--entity-set",
            "Products",
            "--metadata-url",
            METADATA,
            "--output",
            str(output),
        ],
    )
    assert result.exit_code != 0
    assert isinstance(result.exception, DataContractException)
    assert re.search(error, str(result.exception))
    assert not output.exists()
    get.assert_called_once()


@pytest.mark.parametrize("document_version, header_version", [("4.01", "4.0"), ("4.123", "4.1"), ("4.01", "4.1")])
def test_json_version_conflict(metadata_response, json_metadata, document_version, header_version):
    response, _ = metadata_response
    json_metadata["$Version"] = document_version
    response.headers = {"OData-Version": header_version}
    response.content = json.dumps(json_metadata).encode()
    with pytest.raises(DataContractException, match="Conflicting OData versions"):
        import_contract("Products")


@pytest.mark.parametrize("format", ["xml", "json"])
@pytest.mark.parametrize("version", [None, "3.0", "5.0", "4", "4.", "4.x", "4.1.0", "4.01beta", "4.١"])
def test_invalid_document_versions(metadata_response, format, version):
    response, _ = metadata_response
    response.headers = {"OData-Version": "4.01"}
    if format == "json":
        document = json.loads((FIXTURES / "products.json").read_text())
        if version is None:
            document.pop("$Version")
        else:
            document["$Version"] = version
        response.content = json.dumps(document).encode()
    else:
        response.content = (FIXTURES / "products.xml").read_bytes()
        if version is None:
            response.content = response.content.replace(b' Version="4.01"', b"")
        else:
            response.content = response.content.replace(b'Version="4.01"', f'Version="{version}"'.encode())
    with pytest.raises(DataContractException, match="Unsupported OData version"):
        import_contract("Products")


@pytest.mark.parametrize("format", ["xml", "json"])
def test_version_header_whitespace_preserves_version_string(metadata_response, format):
    response, _ = metadata_response
    response.content = (FIXTURES / f"products.{format}").read_bytes().replace(b"4.01", b"4.00123")
    response.headers = {"OData-Version": " 4.00123 "}
    contract = import_contract("Products")
    assert {p.property: p.value for p in contract.servers[0].customProperties}["odataVersion"] == "4.00123"


@pytest.mark.parametrize("prefix", [b" \t\n" * 100, b"\xef\xbb\xbf \t\n"])
def test_xml_detection_with_whitespace_and_bom(metadata_response, prefix):
    response, _ = metadata_response
    response.headers = {"Content-Type": "application/json"}
    response.content = prefix + metadata_xml('<Property Name="Label" Type="Edm.String"/>')
    assert import_contract().schema_[0].properties[0].name == "Label"


def test_xml_encoding_declaration_is_respected(metadata_response):
    response, _ = metadata_response
    response.headers = {}
    document = metadata_xml('<Property Name="Libellé" Type="Edm.String"/>').decode()
    response.content = ('<?xml version="1.0" encoding="iso-8859-1"?>' + document).encode("iso-8859-1")
    assert import_contract().schema_[0].properties[0].name == "Libellé"


@pytest.fixture
def service_response(metadata_response):
    metadata, get = metadata_response
    metadata.content = (FIXTURES / "products.json").read_bytes()
    metadata.headers = {"OData-Version": "4.01"}
    service = Mock(
        content=(FIXTURES / "service-document.json").read_bytes(),
        headers={"OData-Version": "4.01"},
        url=SERVICE_ROOT,
    )
    documents = {SERVICE_ROOT + "$metadata": metadata, METADATA: metadata, SERVICE_ROOT: service}
    get.side_effect = lambda url, **kwargs: documents[url]
    return service, get


@pytest.mark.parametrize("format", ["xml", "json"])
@pytest.mark.parametrize("metadata_source", ["file", "derived_url", "explicit_url"])
@pytest.mark.parametrize("service_source", ["file", "url"])
@pytest.mark.parametrize("root", [SERVICE_ROOT, SERVICE_ROOT.rstrip("/")])
def test_import_all_advertised_sets(metadata_response, service_response, format, metadata_source, service_source, root):
    metadata, _ = metadata_response
    _, get = service_response
    metadata.content = (FIXTURES / f"products.{format}").read_bytes()
    options, expected_requests = {}, []
    if metadata_source == "file":
        options["odata_metadata_file"] = FIXTURES / f"products.{format}"
    elif metadata_source == "explicit_url":
        options["odata_metadata_url"] = METADATA
        expected_requests.append(METADATA)
    else:
        expected_requests.append(SERVICE_ROOT + "$metadata")
    if service_source == "file":
        options["odata_service_root_file"] = FIXTURES / "service-document.json"
    else:
        expected_requests.append(SERVICE_ROOT)
    contract = DataContract.import_from_source("odata", source=root, **options)
    assert contract.name == "Store"
    assert contract.servers[0].location == SERVICE_ROOT
    assert [s.name for s in contract.schema_] == ["Products", "Orders"]
    assert [s.physicalName for s in contract.schema_] == ["Products", "Orders"]
    assert all(s.logicalType == s.physicalType == "object" for s in contract.schema_)
    assert [{p.property: p.value for p in s.customProperties} for s in contract.schema_] == [
        {"odataEntitySet": "Products", "odataEntitySetUrl": SERVICE_ROOT + "products"},
        {"odataEntitySet": "Orders", "odataEntitySetUrl": "https://example.com/fulfilment/orders"},
    ]
    server_properties = {p.property: p.value for p in contract.servers[0].customProperties}
    assert "odataEntitySet" not in server_properties
    assert server_properties["odataVersion"] == "4.01"
    if metadata_source != "file":
        assert server_properties["odataMetadataUrl"] == expected_requests[0]
    schema = json.loads((Path(__file__).parents[1] / "datacontract/schemas/odcs-3.2.0.schema.json").read_text())
    jsonschema.validate(yaml.safe_load(contract.to_yaml()), schema)
    assert [call.args[0] for call in get.call_args_list] == expected_requests
    if service_source == "url":
        assert get.call_args.kwargs["headers"] == {"Accept": "application/json"}
        assert get.call_args.kwargs["timeout"] == 30
        request = requests.Request("GET", SERVICE_ROOT).prepare()
        assert get.call_args.kwargs["auth"](request).headers.get("Authorization") is None


@pytest.mark.parametrize("format", ["xml", "json"])
@pytest.mark.parametrize("version", ODATA_VERSIONS)
def test_cli_multiple_sets_offline_skips_service_file(metadata_response, tmp_path, format, version):
    _, get = metadata_response
    path = tmp_path / "metadata"
    path.write_bytes((FIXTURES / f"products.{format}").read_bytes().replace(b"4.01", version.encode()))
    result = CliRunner().invoke(
        app,
        [
            "import",
            "odata",
            "--service-root-url",
            SERVICE_ROOT,
            "--metadata-file",
            str(path),
            "--service-root-file",
            str(tmp_path / "does-not-exist.json"),
            "--entity-set",
            "Orders",
            "--entity-set",
            "products",
            "--entity-set",
            "ArchivedProducts",
            "--entity-set",
            "Products",
            "--owner",
            "Catalog",
            "--id",
            "catalog",
            "--debug",
        ],
    )
    assert result.exit_code == 0, result.output
    contract = yaml.safe_load(result.stdout)
    assert contract["name"] == "Store" and contract["id"] == "catalog"
    assert contract["team"]["name"] == "Catalog"
    schemas = contract["schema"]
    assert [s["name"] for s in schemas] == ["Orders", "Products", "ArchivedProducts"]
    assert schemas[1]["properties"] == schemas[2]["properties"]
    assert schemas[1]["customProperties"] != schemas[2]["customProperties"]
    get.assert_not_called()


@pytest.mark.parametrize("root", [SERVICE_ROOT, SERVICE_ROOT.rstrip("/")])
def test_derived_metadata_url_with_explicit_selection(metadata_response, root):
    metadata, get = metadata_response
    metadata.content = (FIXTURES / "products.json").read_bytes()
    metadata.headers = {}
    contract = DataContract.import_from_source("odata", source=root, odata_entity_set=["Products", "Orders"])
    get.assert_called_once()
    assert get.call_args.args == (SERVICE_ROOT + "$metadata",)
    assert contract.servers[0].location == root.rstrip("/") + "/"


@pytest.mark.parametrize("selection", [[], "Products", [None], [""], ["  "]])
def test_invalid_explicit_selection_does_not_fetch(metadata_response, selection):
    _, get = metadata_response
    with pytest.raises(DataContractException, match="non-empty list"):
        DataContract.import_from_source("odata", source=SERVICE_ROOT, odata_entity_set=selection)
    get.assert_not_called()


@pytest.mark.parametrize("context_key", ["@odata.context", "@context"])
@pytest.mark.parametrize("context", ["$metadata", "https://example.com/custom/$metadata"])
def test_service_document_url_resolution(service_response, context_key, context):
    service, get = service_response
    service.content = json.dumps(
        {
            context_key: context,
            "value": [
                {"name": "Products", "url": "items/products"},
                {"name": "Orders", "@context": "../shipping/$metadata", "url": "orders"},
                {"name": "Unknown", "kind": "FutureResource", "url": "ignored"},
            ],
        }
    ).encode()
    contract = DataContract.import_from_source("odata", source=SERVICE_ROOT)
    urls = [{p.property: p.value for p in s.customProperties}["odataEntitySetUrl"] for s in contract.schema_]
    directory = "odata" if context == "$metadata" else "custom"
    assert urls == [f"https://example.com/{directory}/items/products", "https://example.com/shipping/orders"]
    assert [call.args[0] for call in get.call_args_list] == [SERVICE_ROOT + "$metadata", SERVICE_ROOT]


@pytest.mark.parametrize("url", ["https://example.com/redirected/", "https://example.com/redirected/service.json"])
@pytest.mark.parametrize("root", [SERVICE_ROOT, SERVICE_ROOT.rstrip("/")])
def test_redirected_service_document_base(service_response, url, root):
    service, get = service_response
    service.url = url
    contract = DataContract.import_from_source("odata", source=root)
    assert contract.schema_[0].customProperties[1].value == "https://example.com/redirected/products"
    assert contract.servers[0].location == SERVICE_ROOT
    assert [call.args[0] for call in get.call_args_list] == [SERVICE_ROOT + "$metadata", SERVICE_ROOT]


@pytest.mark.parametrize("version", [None, *ODATA_VERSIONS])
def test_service_header_does_not_override_csdl_version(service_response, version):
    service, _ = service_response
    service.headers = {"OData-Version": version} if version else {}
    contract = DataContract.import_from_source("odata", source=SERVICE_ROOT)
    assert {p.property: p.value for p in contract.servers[0].customProperties}["odataVersion"] == "4.01"


@pytest.mark.parametrize("target", ["metadata", "service"])
@pytest.mark.parametrize("version", ["", "3.0", "5.0", "4", "4.", "4.x", "4.1.0"])
def test_invalid_http_versions(metadata_response, service_response, target, version):
    metadata, _ = metadata_response
    service, _ = service_response
    response = metadata if target == "metadata" else service
    response.headers = {"OData-Version": version}
    with pytest.raises(DataContractException, match="Unsupported OData version"):
        DataContract.import_from_source("odata", source=SERVICE_ROOT)


@pytest.mark.parametrize(
    "document,error",
    [
        ({}, "context URL"),
        ({"@context": None, "value": []}, "Invalid context URL"),
        ({"@context": "http://[", "value": []}, "Invalid context URL"),
        ({"@context": "$metadata", "@odata.context": "other", "value": []}, "Conflicting context"),
        ({"@context": "$metadata", "value": {}}, "value array"),
        ({"@context": "$metadata", "value": []}, "No EntitySets"),
        ({"@context": "$metadata", "value": [None]}, "JSON object"),
        ({"@context": "$metadata", "value": [{"name": "Products", "url": "Products", "kind": 1}]}, "Invalid kind"),
        ({"@context": "$metadata", "value": [{"name": "Products"}]}, "name and url"),
        ({"@context": "$metadata", "value": [{"name": 1, "url": "Products"}]}, "name and url"),
        ({"@context": "$metadata", "value": [{"name": "Products", "url": "file:///tmp/data"}]}, "Invalid .*URL"),
        ({"@context": "$metadata", "value": [{"name": "Products", "url": "http://["}]}, "Invalid service document URL"),
        ({"@context": "$metadata", "value": [{"name": "Absent", "url": "Absent"}]}, "not found"),
        ({"@context": "$metadata", "value": [{"name": "Products", "url": "Products"}] * 2}, "Duplicate EntitySet"),
        (
            {
                "@context": "$metadata",
                "value": [{"name": "products", "url": "Products"}, {"name": "Products", "url": "Products"}],
            },
            "Duplicate EntitySet",
        ),
    ],
)
def test_invalid_service_documents(service_response, tmp_path, document, error):
    service, _ = service_response
    service.content = json.dumps(document).encode()
    output = tmp_path / "contract.yaml"
    output.write_text("existing contract")
    result = CliRunner().invoke(app, ["import", "odata", "--service-root-url", SERVICE_ROOT, "--output", str(output)])
    assert result.exit_code != 0 and isinstance(result.exception, DataContractException)
    assert re.search(error, str(result.exception))
    assert output.read_text() == "existing contract"


@pytest.mark.parametrize("content", [b"<service/>", b"{", b'{"value":[],"value":[]}'])
def test_service_document_invalid_json(service_response, content):
    service, _ = service_response
    service.content = content
    with pytest.raises(DataContractException, match="Invalid or unsafe|Duplicate JSON key"):
        DataContract.import_from_source("odata", source=SERVICE_ROOT)


@pytest.mark.parametrize("failure", ["http", "timeout", "version"])
def test_service_document_transport_errors(service_response, failure):
    service, get = service_response
    if failure == "http":
        service.raise_for_status.side_effect = requests.HTTPError("HTTP 403")
    elif failure == "timeout":
        previous = get.side_effect

        def fetch(url, **kwargs):
            if url == SERVICE_ROOT:
                raise requests.Timeout("timed out")
            return previous(url, **kwargs)

        get.side_effect = fetch
    else:
        service.headers = {"OData-Version": "3.0"}
    with pytest.raises(DataContractException, match="Failed to fetch OData service document|Unsupported OData version"):
        DataContract.import_from_source("odata", source=SERVICE_ROOT)


def test_missing_service_file_does_not_fall_back_to_network(metadata_response, tmp_path):
    _, get = metadata_response
    with pytest.raises(DataContractException, match="Failed to read OData service document file"):
        DataContract.import_from_source(
            "odata",
            source=SERVICE_ROOT,
            odata_metadata_file=FIXTURES / "products.xml",
            odata_service_root_file=tmp_path / "missing.json",
        )
    get.assert_not_called()


def test_cli_offline_all_sets(metadata_response, tmp_path):
    _, get = metadata_response
    output = tmp_path / "contract.yaml"
    result = CliRunner().invoke(
        app,
        [
            "import",
            "odata",
            "--service-root-url",
            SERVICE_ROOT,
            "--metadata-file",
            str(FIXTURES / "products.xml"),
            "--service-root-file",
            str(FIXTURES / "service-document.json"),
            "--output",
            str(output),
        ],
    )
    assert result.exit_code == 0, result.output
    assert [s["name"] for s in yaml.safe_load(output.read_text())["schema"]] == ["Products", "Orders"]
    get.assert_not_called()


def test_failure_in_later_selected_schema_preserves_output(metadata_response, json_metadata, tmp_path):
    metadata, get = metadata_response
    json_metadata["Catalog.Model"]["Order"]["Total"]["$Type"] = "Edm.Binary"
    metadata.content = json.dumps(json_metadata).encode()
    output = tmp_path / "contract.yaml"
    output.write_text("existing contract")
    result = CliRunner().invoke(
        app,
        [
            "import",
            "odata",
            "--service-root-url",
            SERVICE_ROOT,
            "--metadata-url",
            METADATA,
            "--entity-set",
            "Products",
            "--entity-set",
            "Orders",
            "--output",
            str(output),
        ],
    )
    assert result.exit_code != 0 and isinstance(result.exception, DataContractException)
    assert "Orders.Total" in str(result.exception)
    assert output.read_text() == "existing contract"
    get.assert_called_once()


def test_xml_requires_unambiguous_container(metadata_response):
    metadata, _ = metadata_response
    metadata.headers = {}
    metadata.content = metadata_xml(extra_schema='<EntityContainer Name="AnotherService"/>')
    with pytest.raises(DataContractException, match="EntityContainer.*ambiguous"):
        import_contract()


@pytest.mark.parametrize("authorization", [None, "Bearer synthetic-token", "Basic dXNlcjpwYXNz"])
@pytest.mark.parametrize("config_source", ["environment", "config", "dict"])
def test_authentication_on_both_documents(service_response, monkeypatch, authorization, config_source):
    _, get = service_response
    config = None
    if config_source == "environment":
        if authorization is not None:
            monkeypatch.setenv("DATACONTRACT_API_HEADER_AUTHORIZATION", authorization)
    elif authorization is not None:
        monkeypatch.setenv("DATACONTRACT_API_HEADER_AUTHORIZATION", "Bearer overridden-token")
        config = (
            Config(api_header_authorization=authorization)
            if config_source == "config"
            else {"DATACONTRACT_API_HEADER_AUTHORIZATION": authorization}
        )
    contract = DataContract.import_from_source("odata", source=SERVICE_ROOT, odata_metadata_url=METADATA, config=config)
    assert [call.args[0] for call in get.call_args_list] == [METADATA, SERVICE_ROOT]
    for call in get.call_args_list:
        headers = call.kwargs["headers"]
        assert headers.get("Authorization") == authorization
        if authorization is None:
            assert "Authorization" not in headers
    if authorization is not None:
        assert authorization not in contract.to_yaml()


def test_cli_authentication_from_config_file(service_response, tmp_path, monkeypatch):
    _, get = service_response
    monkeypatch.setenv("DATACONTRACT_API_HEADER_AUTHORIZATION", "Bearer overridden-token")
    monkeypatch.setenv("ODATA_TEST_AUTH", "Bearer config-file-token")
    config_file = tmp_path / "config.yaml"
    config_file.write_text('api_header_authorization: "${ODATA_TEST_AUTH}"\n')
    result = CliRunner().invoke(
        app,
        ["--config-file", str(config_file), "import", "odata", "--service-root-url", SERVICE_ROOT],
    )
    assert result.exit_code == 0, result.output
    assert len(get.call_args_list) == 2
    assert all(call.kwargs["headers"]["Authorization"] == "Bearer config-file-token" for call in get.call_args_list)
    assert "config-file-token" not in result.output
    assert "overridden-token" not in result.output


@pytest.mark.parametrize("selection", [True, False])
def test_authenticated_offline_import(metadata_response, selection):
    _, get = metadata_response
    options = (
        {"odata_entity_set": ["Products"]}
        if selection
        else {"odata_service_root_file": FIXTURES / "service-document.json"}
    )
    contract = DataContract.import_from_source(
        "odata",
        source=SERVICE_ROOT,
        odata_metadata_file=FIXTURES / "products.xml",
        config=Config(api_header_authorization="Bearer offline-token"),
        **options,
    )
    get.assert_not_called()
    assert "offline-token" not in contract.to_yaml()


@pytest.fixture
def http_transport(monkeypatch):
    # Exercise real request preparation and redirects; only the adapter's I/O is mocked.
    routes = {
        SERVICE_ROOT + "$metadata": (200, {}, (FIXTURES / "products.json").read_bytes()),
        SERVICE_ROOT: (200, {}, (FIXTURES / "service-document.json").read_bytes()),
    }
    sent = []

    def send(adapter, request, **kwargs):
        sent.append((request, kwargs))
        status, headers, content = routes[request.url]
        response = requests.Response()
        response.status_code = status
        response.headers.update(headers)
        response._content = content
        response.raw = BytesIO(content)
        response.request = request
        response.url = request.url
        return response

    monkeypatch.setattr(requests.adapters.HTTPAdapter, "send", send)
    return routes, sent


@pytest.mark.parametrize("authorization", [None, "Bearer redirect-token"])
@pytest.mark.parametrize("target", ["metadata", "service"])
@pytest.mark.parametrize(
    "redirect_url, retained",
    [
        ("https://example.com/redirected/document", True),
        ("https://other.example.com/document", False),
        ("http://example.com/document", False),
    ],
)
def test_redirect_authentication(http_transport, monkeypatch, authorization, target, redirect_url, retained):
    routes, sent = http_transport
    netrc = Mock(return_value=("unexpected-user", "unexpected-password"))
    monkeypatch.setattr("requests.sessions.get_netrc_auth", netrc)
    initial_url = SERVICE_ROOT + "$metadata" if target == "metadata" else SERVICE_ROOT
    final_url = initial_url + "final"
    document = routes[initial_url]
    routes[initial_url] = (302, {"Location": redirect_url}, b"")
    routes[redirect_url] = (302, {"Location": final_url}, b"")
    routes[final_url] = document
    DataContract.import_from_source("odata", source=SERVICE_ROOT, config=Config(api_header_authorization=authorization))
    requests_by_url = {request.url: request for request, _ in sent}
    assert requests_by_url[initial_url].headers.get("Authorization") == authorization
    expected = authorization if retained else None
    assert requests_by_url[redirect_url].headers.get("Authorization") == expected
    # Returning to the initial host must not restore credentials removed earlier.
    assert requests_by_url[final_url].headers.get("Authorization") == expected
    netrc.assert_not_called()


def test_authentication_preserves_proxy_and_certificate_environment(http_transport, monkeypatch):
    _, sent = http_transport
    monkeypatch.setenv("HTTPS_PROXY", "http://proxy.example.com:8080")
    monkeypatch.setenv("NO_PROXY", "")
    monkeypatch.setenv("REQUESTS_CA_BUNDLE", "/synthetic/ca.pem")
    DataContract.import_from_source(
        "odata", source=SERVICE_ROOT, config=Config(api_header_authorization="Bearer proxy-token")
    )
    assert len(sent) == 2
    for request, options in sent:
        assert request.headers["Authorization"] == "Bearer proxy-token"
        assert options["proxies"]["https"] == "http://proxy.example.com:8080"
        assert options["verify"] == "/synthetic/ca.pem"


@pytest.mark.parametrize("failure", [401, 403, "invalid_header"])
@pytest.mark.parametrize("target", ["metadata", "service"])
def test_authentication_errors_do_not_expose_secrets(http_transport, tmp_path, monkeypatch, caplog, failure, target):
    routes, _ = http_transport
    secret = "Bearer confidential-test-token"
    if failure == "invalid_header":
        secret += "\ninvalid"
    else:
        url = SERVICE_ROOT + "$metadata" if target == "metadata" else SERVICE_ROOT
        routes[url] = (failure, {}, secret.encode())
    monkeypatch.setenv("DATACONTRACT_API_HEADER_AUTHORIZATION", secret)
    output = tmp_path / "contract.yaml"
    output.write_text("existing contract")
    args = ["import", "odata", "--service-root-url", SERVICE_ROOT, "--output", str(output), "--debug"]
    if target == "service":
        args += ["--metadata-file", str(FIXTURES / "products.json")]
    result = CliRunner().invoke(app, args)
    assert result.exit_code != 0
    assert isinstance(result.exception, DataContractException)
    assert result.exception.type == "connection"
    assert ("InvalidHeader" if failure == "invalid_header" else f"HTTP {failure}") in str(result.exception)
    assert result.exception.original_exception is None
    rendered = result.output + "".join(traceback.format_exception(result.exception)) + caplog.text
    assert "confidential-test-token" not in rendered
    assert output.read_text() == "existing contract"
