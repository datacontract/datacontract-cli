import avro.schema

from datacontract.model.data_contract_specification import \
    DataContractSpecification, Model, Field


def import_avro(data_contract_specification: DataContractSpecification, source: str):

    if data_contract_specification.models is None:
            data_contract_specification.models = {}

    fields = {}
    avro_schema = avro.schema.parse(open(source, "rb").read())
    
    #TODO: avro_schema.getType

    for field in avro_schema.fields:
        field_name = field.name
        field_type = map_type_from_avro(field.type)
        field_required = field.is_nullable()

        field_obj = Field()
        field_obj.type = field_type
        field_obj.required = field_required

        fields[field_name] = field_obj

    table_name = avro_schema.name
    data_contract_specification.models[table_name] = Model(
        type="table",
        fields=fields,
    )

    return data_contract_specification


def map_type_from_avro(avro_type: str):
    if avro_type is None:
        return None
    
    #TODO: ambiguous mapping in the export
    if avro_type == "null":
        return None
    elif avro_type == "string":
        return "string"
    elif avro_type == "bytes":
        return "binary"
    elif avro_type == "double":
        return "double"
    elif avro_type == "int":
        return "integer"
    elif avro_type == "long":
        return "long"
    elif avro_type == "boolean":
        return "boolean"
    elif avro_type == "array":
        return "array"
    #TODO: type record
    else:
        return "variant"