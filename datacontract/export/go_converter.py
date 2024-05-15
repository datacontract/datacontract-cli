import datacontract.model.data_contract_specification as spec
from typing import List
import re


def to_go_types(contract: spec.DataContractSpecification) -> str:
    result = "package main\n\n"

    for key in contract.models.keys():
        go_types = generate_go_struct(contract.models[key], key)
        for go_struct in go_types:
            # print(go_struct + "\n\n")
            result += f"\n{go_struct}\n"

    return result


def python_type_to_go_type(py_type) -> str:
    match py_type:
        case "text":
            return "string"
        case "timestamp":
            return "time.Time"
        case "long":
            return "int64"
        case "int":
            return "int"
        case "float":
            return "float64"
        case "boolean":
            return "bool"
        case _:
            return "interface{}"


def to_camel_case(snake_str) -> str:
    return "".join(word.capitalize() for word in re.split(r"_|(?<!^)(?=[A-Z])", snake_str))


def get_subtype(field_info, nested_structs, struct_name, camel_case_name) -> str:
    go_type = "interface{}"
    if field_info.fields:
        nested_struct_name = to_camel_case(f"{struct_name}_{camel_case_name}")
        nested_structs[nested_struct_name] = field_info.fields
        go_type = nested_struct_name

    match field_info.type:
        case "array":
            if field_info.items:
                item_type = get_subtype(field_info.items, nested_structs, struct_name, camel_case_name + "Item")
                go_type = f"[]{item_type}"
            else:
                go_type = "[]interface{}"
        case "record":
            if field_info.fields:
                nested_struct_name = to_camel_case(f"{struct_name}_{camel_case_name}")
                nested_structs[nested_struct_name] = field_info.fields
                go_type = nested_struct_name
            else:
                go_type = "interface{}"
        case "object":
            pass
        case _:
            go_type = field_info.type

    return go_type


def generate_go_struct(model, model_name) -> List[str]:
    go_types = []
    struct_name = to_camel_case(model_name)
    lines = [f"type {struct_name} struct {{"]

    nested_structs = {}

    for field_name, field_info in model.fields.items():
        go_type = python_type_to_go_type(field_info.type)
        camel_case_name = to_camel_case(field_name)
        json_tag = field_name if field_info.required else f"{field_name},omitempty"
        avro_tag = field_name

        if go_type == "interface{}":
            go_type = get_subtype(field_info, nested_structs, struct_name, camel_case_name)
        # else:
        #     go_type = field_info, go_type)

        go_type = go_type if field_info.required else f"*{go_type}"

        lines.append(
            f'    {camel_case_name} {go_type} `json:"{json_tag}" avro:"{avro_tag}"`  // {field_info.description}'
        )
    lines.append("}")
    go_types.append("\n".join(lines))

    for nested_struct_name, nested_fields in nested_structs.items():
        nested_model = spec.Model(fields=nested_fields)
        nested_go_types = generate_go_struct(nested_model, nested_struct_name)
        go_types.extend(nested_go_types)

    return go_types
