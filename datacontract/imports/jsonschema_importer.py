import json

import fastjsonschema

from datacontract.imports.importer import Importer
from datacontract.model.data_contract_specification import DataContractSpecification, Model, Field, Definition
from datacontract.model.exceptions import DataContractException


class JsonSchemaImporter(Importer):
    def import_source(
        self, data_contract_specification: DataContractSpecification, source: str, import_args: dict
    ) -> dict:
        return import_jsonschema(data_contract_specification, source)


def convert_json_schema_properties(properties, is_definition=False):
    fields = {}
    for field_name, field_schema in properties.items():
        field_kwargs = {}
        field_type = field_schema.get("type")

        # Determine if the field is required and set the type to the non-null option if applicable
        if isinstance(field_type, list) and "null" in field_type:
            field_kwargs["required"] = False
            non_null_types = [t for t in field_type if t != "null"]
            if non_null_types:
                field_type = non_null_types[0]
            else:
                field_type = None
        else:
            field_kwargs["required"] = True

        # Set the non-null type
        if field_type:
            field_kwargs["type"] = field_type

        for key, value in field_schema.items():
            match key:
                case "title":
                    field_kwargs["title"] = value
                case "type":
                    pass  # type is already handled above
                case "format":
                    field_kwargs["format"] = value
                case "description":
                    field_kwargs["description"] = value
                case "pattern":
                    field_kwargs["pattern"] = value
                case "minLength":
                    field_kwargs["minLength"] = value
                case "maxLength":
                    field_kwargs["maxLength"] = value
                case "minimum":
                    field_kwargs["minimum"] = value
                case "exclusiveMinimum":
                    field_kwargs["exclusiveMinimum"] = value
                case "maximum":
                    field_kwargs["maximum"] = value
                case "exclusiveMaximum":
                    field_kwargs["exclusiveMaximum"] = value
                case "enum":
                    field_kwargs["enum"] = value
                case "tags":
                    field_kwargs["tags"] = value
                case "properties":
                    field_kwargs["fields"] = convert_json_schema_properties(value)
                case "items":
                    field_kwargs["items"] = convert_json_schema_properties(value)

        field = Field(**field_kwargs)
        fields[field_name] = field

    return fields


def import_jsonschema(data_contract_specification: DataContractSpecification, source: str) -> DataContractSpecification:
    if data_contract_specification.models is None:
        data_contract_specification.models = {}

    try:
        with open(source, "r") as file:
            json_schema = json.loads(file.read())
            validator = fastjsonschema.compile({})
            validator(json_schema)

            model = Model(
                description=json_schema.get("description"),
                type=json_schema.get("type"),
                title=json_schema.get("title"),
                fields=convert_json_schema_properties(json_schema.get("properties", {})),
            )
            data_contract_specification.models[json_schema.get("title", "default_model")] = model

            if "definitions" in json_schema:
                for def_name, def_schema in json_schema["definitions"].items():
                    definition_kwargs = {}

                    for key, value in def_schema.items():
                        match key:
                            case "domain":
                                definition_kwargs["domain"] = value
                            case "title":
                                definition_kwargs["title"] = value
                            case "description":
                                definition_kwargs["description"] = value
                            case "type":
                                definition_kwargs["type"] = value
                            case "enum":
                                definition_kwargs["enum"] = value
                            case "format":
                                definition_kwargs["format"] = value
                            case "minLength":
                                definition_kwargs["minLength"] = value
                            case "maxLength":
                                definition_kwargs["maxLength"] = value
                            case "pattern":
                                definition_kwargs["pattern"] = value
                            case "minimum":
                                definition_kwargs["minimum"] = value
                            case "exclusiveMinimum":
                                definition_kwargs["exclusiveMinimum"] = value
                            case "maximum":
                                definition_kwargs["maximum"] = value
                            case "exclusiveMaximum":
                                definition_kwargs["exclusiveMaximum"] = value
                            case "pii":
                                definition_kwargs["pii"] = value
                            case "classification":
                                definition_kwargs["classification"] = value
                            case "tags":
                                definition_kwargs["tags"] = value
                            case "properties":
                                definition_kwargs["fields"] = convert_json_schema_properties(value, is_definition=True)

                    definition = Definition(name=def_name, **definition_kwargs)
                    data_contract_specification.definitions[def_name] = definition

    except fastjsonschema.JsonSchemaException as e:
        raise DataContractException(
            type="schema",
            name="Parse json schema",
            reason=f"Failed to parse json schema from {source}: {e}",
            engine="datacontract",
        )

    except Exception as e:
        raise DataContractException(
            type="schema",
            name="Parse json schema",
            reason=f"Failed to parse json schema from {source}",
            engine="datacontract",
            original_exception=e,
        )

    return data_contract_specification
