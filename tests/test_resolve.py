import tempfile

from datacontract.lint.resolve import resolve_data_contract
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
