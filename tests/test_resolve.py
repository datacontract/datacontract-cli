import tempfile

import pytest

from datacontract.data_contract import DataContract
from datacontract.lint.resolve import _to_yaml, resolve_data_contract
from datacontract.model.exceptions import DataContractException
from datacontract.model.server import get_server_type

# logging.basicConfig(level=logging.INFO, force=True)


def test_resolve_dcs_inlines_definition():
    odcs = resolve_data_contract(
        data_contract_str="""
    dataContractSpecification: 1.2.1
    id: my-id
    info:
      title: My Title
      version: 1.0.0
    models:
      orders:
        fields:
          order_id:
            $ref: "#/definitions/order_id"
    definitions:
      order_id:
        name: order_id
        type: int
    """,
        inline_references=True,
    )
    # ODCS uses schema_ (list) with properties (list) and logicalType
    orders_schema = next(s for s in odcs.schema_ if s.name == "orders")
    order_id_prop = next(p for p in orders_schema.properties if p.name == "order_id")
    assert order_id_prop.logicalType == "integer"


def test_resolve_data_contract_complex_definition():
    odcs = resolve_data_contract(
        data_contract_str="""
    dataContractSpecification: 1.2.1
    id: my-id
    info:
      title: My Title
      version: 1.0.0
    models:
      orders:
        fields:
          order_id:
            $ref: "#/definitions/order/fields/order_id"
    definitions:
      order:
        name: order
        type: object
        fields:
          order_id:
            type: int
    """,
        inline_references=True,
    )
    orders_schema = next(s for s in odcs.schema_ if s.name == "orders")
    order_id_prop = next(p for p in orders_schema.properties if p.name == "order_id")
    assert order_id_prop.logicalType == "integer"


def test_resolve_data_contract_array_definition():
    odcs = resolve_data_contract(
        data_contract_str="""
    dataContractSpecification: 1.2.1
    id: my-id
    info:
      title: My Title
      version: 1.0.0
    models:
      my_message:
        fields:
          my_data:
            type: array
            items:
              name: My Data
              type: object
              fields:
                data_id:
                  $ref: "#/definitions/order_id"
                  required: true
    definitions:
      order_id:
        name: order_id
        type: int
    """,
        inline_references=True,
    )
    my_message_schema = next(s for s in odcs.schema_ if s.name == "my_message")
    my_data_prop = next(p for p in my_message_schema.properties if p.name == "my_data")
    data_id_prop = next(p for p in my_data_prop.items.properties if p.name == "data_id")
    assert data_id_prop.logicalType == "integer"


def test_resolve_data_contract_nested_definition():
    odcs = resolve_data_contract(
        data_contract_str="""
    dataContractSpecification: 1.2.1
    id: my-id
    info:
      title: My Title
      version: 1.0.0
    models:
      my_message:
        fields:
          my_data:
            name: My Data
            type: object
            fields:
              data_id:
                $ref: "#/definitions/order_id"
                required: true
    definitions:
      order_id:
        name: order_id
        type: int
    """,
        inline_references=True,
    )
    my_message_schema = next(s for s in odcs.schema_ if s.name == "my_message")
    my_data_prop = next(p for p in my_message_schema.properties if p.name == "my_data")
    data_id_prop = next(p for p in my_data_prop.properties if p.name == "data_id")
    assert data_id_prop.logicalType == "integer"


def test_resolve_data_contract_simple_definition_file():
    with tempfile.NamedTemporaryFile(delete=True) as temp_file:
        # create temp file with content
        temp_file.write(b"""
        name: order_id
        type: int
        """)
        temp_file.flush()
        print(temp_file.name)

        odcs = resolve_data_contract(
            data_contract_str=f"""
        dataContractSpecification: 1.2.1
        id: my-id
        info:
          title: My Title
          version: 1.0.0
        models:
          orders:
            fields:
              order_id:
                $ref: "file://{temp_file.name}"
        """,
            inline_references=True,
        )
        orders_schema = next(s for s in odcs.schema_ if s.name == "orders")
        order_id_prop = next(p for p in orders_schema.properties if p.name == "order_id")
        assert order_id_prop.logicalType == "integer"


def test_resolve_data_contract_complex_definition_file():
    with tempfile.NamedTemporaryFile(delete=True) as temp_file:
        # create temp file with content
        temp_file.write(b"""
        name: order
        type: object
        fields:
          order_id:
            type: int
        """)
        temp_file.flush()
        print(temp_file.name)

        odcs = resolve_data_contract(
            data_contract_str=f"""
        dataContractSpecification: 1.2.1
        id: my-id
        info:
          title: My Title
          version: 1.0.0
        models:
          orders:
            fields:
              order_id:
                $ref: "file://{temp_file.name}#/fields/order_id"
        """,
            inline_references=True,
        )
        orders_schema = next(s for s in odcs.schema_ if s.name == "orders")
        order_id_prop = next(p for p in orders_schema.properties if p.name == "order_id")
        assert order_id_prop.logicalType == "integer"


def test_resolve_data_contract_relative_refrence():
    with tempfile.TemporaryDirectory() as temp_dir:
        # create temp file with content
        with open(f"{temp_dir}/order.yaml", "w") as temp_file:
            temp_file.write("""
            definitions:
              order_id:
                title: order id
                type: text
                examples:
                  - O1234
                pii: True
                classification: restricted
                tags:
                  - policy
            """)
            temp_file.flush()
            print(temp_file.name)

        odcs = resolve_data_contract(
            data_contract_str=f"""
        dataContractSpecification: 1.2.1
        id: my-id
        info:
          title: My Title
          version: 1.0.0
        models:
          orders:
            fields:
              order_id:
                $ref: "file://{temp_dir}/order.yaml#/definitions/order_id"
        """,
            inline_references=True,
        )
        orders_schema = next(s for s in odcs.schema_ if s.name == "orders")
        order_id_prop = next(p for p in orders_schema.properties if p.name == "order_id")
        assert order_id_prop.logicalType == "string"


def test_resolve_odcs_custom_dataframe_server():
    # `dataframe` is not an ODCS server type, so it is expressed standard-compliantly
    # as `type: custom` with the real type in the `customType` custom property.
    # Resolving (which runs JSON-schema validation) must not reject it. See issue #1282.
    odcs = resolve_data_contract(
        data_contract_str="""
    kind: DataContract
    apiVersion: v3.1.0
    id: repro
    version: 1.0.0
    status: active
    servers:
      - server: production
        type: custom
        customProperties:
          - property: customType
            value: dataframe
    schema:
      - name: my_table
        properties:
          - name: c
            logicalType: string
    """,
    )
    assert odcs.servers[0].type == "custom"
    assert get_server_type(odcs.servers[0]) == "dataframe"


def test_resolve_dcs_dataframe_server_converted_to_custom():
    # The DCS -> ODCS converter must emit a standard-compliant `type: custom`
    # server for the non-ODCS `dataframe` type. See issue #1282.
    odcs = resolve_data_contract(
        data_contract_str="""
    dataContractSpecification: 1.2.1
    id: my-id
    info:
      title: My Title
      version: 1.0.0
    servers:
      unittest:
        type: dataframe
    models:
      my_table:
        fields:
          c:
            type: string
    """,
    )
    assert odcs.servers[0].type == "custom"
    assert get_server_type(odcs.servers[0]) == "dataframe"


def test_resolve_dcs_status_defaults_to_draft():
    odcs = resolve_data_contract(
        data_contract_str="""
    dataContractSpecification: 1.2.1
    id: my-id
    info:
      title: My Title
      version: 1.0.0
    models:
      my_table:
        fields:
          c:
            type: string
    """,
    )
    assert odcs.status == "draft"


def test_resolve_dcs_status_preserved_when_set():
    odcs = resolve_data_contract(
        data_contract_str="""
    dataContractSpecification: 1.2.1
    id: my-id
    info:
      title: My Title
      version: 1.0.0
      status: active
    models:
      my_table:
        fields:
          c:
            type: string
    """,
    )
    assert odcs.status == "active"


@pytest.mark.parametrize(
    "document",
    [
        "status: active\nstatus: draft\n",
        "schema:\n- name: orders\n  properties:\n  - name: id\n    required: true\n    required: false\n",
        "schema:\n- name: orders\n  quality: {type: sql, query: SELECT 1, query: SELECT 2}\n",
    ],
)
def test_duplicate_mapping_keys_are_rejected(document: str) -> None:
    with pytest.raises(DataContractException, match="duplicate key"):
        _to_yaml(document)


def test_duplicate_key_error_identifies_source_and_line() -> None:
    with pytest.raises(DataContractException) as exc:
        _to_yaml("version: 1.0.0\nversion: 2.0.0\n", "contracts/orders.yaml")
    assert "contracts/orders.yaml" in str(exc.value)
    assert "line 2" in str(exc.value)


def test_yaml_merge_allows_explicit_override() -> None:
    parsed = _to_yaml("defaults: &defaults {required: false}\ncolumn: {<<: *defaults, required: true}\n")
    assert parsed["column"]["required"] is True


def test_yaml_merge_does_not_hide_duplicate_explicit_keys() -> None:
    with pytest.raises(DataContractException, match="duplicate key"):
        _to_yaml("defaults: &defaults {required: false}\ncolumn: {<<: *defaults, required: true, required: false}\n")


def test_date_strings_and_distinct_mapping_keys_are_unchanged() -> None:
    parsed = _to_yaml("date: 2026-10-13\nfirst: {name: id}\nsecond: {name: id}\n")
    assert parsed["date"] == "2026-10-13"
    assert parsed["first"] == parsed["second"] == {"name": "id"}


def test_lint_reports_duplicate_keys_as_a_failed_check() -> None:
    run = DataContract(data_contract_str="apiVersion: v3.0.2\napiVersion: v3.2.0\n").lint()
    assert not run.has_passed()
    assert any("duplicate key" in (check.reason or "") for check in run.checks)
