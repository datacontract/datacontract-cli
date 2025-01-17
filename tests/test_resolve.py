import tempfile

from datacontract.lint.resolve import resolve_data_contract

# logging.basicConfig(level=logging.INFO, force=True)


def test_resolve_data_contract_simple_definition():
    datacontract = resolve_data_contract(
        data_contract_str="""
    dataContractSpecification: 1.1.0
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
        inline_definitions=True,
    )
    assert datacontract.models["orders"].fields["order_id"].type == "int"


def test_resolve_data_contract_complex_definition():
    datacontract = resolve_data_contract(
        data_contract_str="""
    dataContractSpecification: 1.1.0
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
        inline_definitions=True,
    )
    assert datacontract.models["orders"].fields["order_id"].type == "int"


def test_resolve_data_contract_array_definition():
    datacontract = resolve_data_contract(
        data_contract_str="""
    dataContractSpecification: 1.1.0
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
        inline_definitions=True,
    )
    assert datacontract.models["my_message"].fields["my_data"].items.fields["data_id"].type == "int"


def test_resolve_data_contract_nested_definition():
    datacontract = resolve_data_contract(
        data_contract_str="""
    dataContractSpecification: 1.1.0
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
        inline_definitions=True,
    )
    assert datacontract.models["my_message"].fields["my_data"].fields["data_id"].type == "int"


def test_resolve_data_contract_simple_definition_file():
    with tempfile.NamedTemporaryFile(delete=True) as temp_file:
        # create temp file with content
        temp_file.write(b"""
        name: order_id
        type: int
        """)
        temp_file.flush()
        print(temp_file.name)

        datacontract = resolve_data_contract(
            data_contract_str=f"""
        dataContractSpecification: 1.1.0
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
            inline_definitions=True,
        )
        assert datacontract.models["orders"].fields["order_id"].type == "int"


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

        datacontract = resolve_data_contract(
            data_contract_str=f"""
        dataContractSpecification: 1.1.0
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
            inline_definitions=True,
        )
        assert datacontract.models["orders"].fields["order_id"].type == "int"
