from typing import Dict

import yaml

from datacontract.export.sql_type_converter import convert_to_sql_type
from datacontract.model.data_contract_specification import DataContractSpecification, Model, Field

from datacontract.export.exporter import Exporter 
# if export_format == "dbt":
#     return to_dbt_models_yaml(data_contract)

# if export_format == "dbt-sources":
#     return to_dbt_sources_yaml(data_contract, self._server)

# if export_format == "dbt-staging-sql":
#     model_name, model_value = exporter._check_models_for_export(data_contract, model, export_format)
#     return to_dbt_staging_sql(data_contract, model_name, model_value)
        
        
class DBTExporter(Exporter):
    def export(self, export_args) -> dict:
        self.dict_args = export_args  
    
        return self.to_dbt_models_yaml(
            self.dict_args.get('data_contract'),
            self.dict_args.get('server_type')
            )

    def to_dbt_models_yaml(self, data_contract_spec: DataContractSpecification, server_type: str):
        dbt = {
            "version": 2,
            "models": [],
        }
        for model_key, model_value in data_contract_spec.models.items():
            dbt_model = self._to_dbt_model(model_key, model_value, data_contract_spec, server_type)
            dbt["models"].append(dbt_model)
        return yaml.dump(dbt, indent=2, sort_keys=False, allow_unicode=True)

    def _to_dbt_source_table(self, model_key, model_value: Model, sql_type: str) -> dict:
        dbt_model = {
            "name": model_key,
        }

        if model_value.description is not None:
            dbt_model["description"] = model_value.description
        columns = self._to_columns(model_value.fields, False, False, sql_type)
        if columns:
            dbt_model["columns"] = columns
        return dbt_model


    def _to_dbt_model(self, model_key, model_value: Model, data_contract_spec: DataContractSpecification, sql_type: str) -> dict:
        dbt_model = {
            "name": model_key,
        }
        model_type = self._to_dbt_model_type(model_value.type)
        dbt_model["config"] = {"meta": {"data_contract": data_contract_spec.id}}
        dbt_model["config"]["materialized"] = model_type

        if data_contract_spec.info.owner is not None:
            dbt_model["config"]["meta"]["owner"] = data_contract_spec.info.owner

        if self._supports_constraints(model_type):
            dbt_model["config"]["contract"] = {"enforced": True}
        if model_value.description is not None:
            dbt_model["description"] = model_value.description
        columns = self._to_columns(model_value.fields, self._supports_constraints(model_type), True,sql_type)
        if columns:
            dbt_model["columns"] = columns
        return dbt_model


    def _to_dbt_model_type(self, model_type):
        # https://docs.getdbt.com/docs/build/materializations
        # Allowed values: table, view, incremental, ephemeral, materialized view
        # Custom values also possible
        if model_type is None:
            return "table"
        if model_type.lower() == "table":
            return "table"
        if model_type.lower() == "view":
            return "view"
        return "table"


    def _supports_constraints(self, model_type):
        return model_type == "table" or model_type == "incremental"


    def _to_columns(self, fields: Dict[str, Field], supports_constraints: bool, supports_datatype: bool, sql_type:str) -> list:
        columns = []
        for field_name, field in fields.items():
            column = self._to_column(field, supports_constraints, supports_datatype, sql_type)
            column["name"] = field_name
            columns.append(column)
        return columns


    def _to_column(self, field: Field, supports_constraints: bool, supports_datatype: bool, sql_type:str="snowflake") -> dict:
        column = {}
        dbt_type = convert_to_sql_type(field, sql_type)
        if dbt_type is not None:
            if supports_datatype:
                column["data_type"] = dbt_type
            else:
                column.setdefault("tests", []).append(
                    {"dbt_expectations.dbt_expectations.expect_column_values_to_be_of_type": {"column_type": dbt_type}}
                )
        if field.description is not None:
            column["description"] = field.description
        if field.required:
            if supports_constraints:
                column.setdefault("constraints", []).append({"type": "not_null"})
            else:
                column.setdefault("tests", []).append("not_null")
        if field.unique:
            if supports_constraints:
                column.setdefault("constraints", []).append({"type": "unique"})
            else:
                column.setdefault("tests", []).append("unique")
        if field.enum is not None and len(field.enum) > 0:
            column.setdefault("tests", []).append({"accepted_values": {"values": field.enum}})
        if field.minLength is not None or field.maxLength is not None:
            length_test = {}
            if field.minLength is not None:
                length_test["min_value"] = field.minLength
            if field.maxLength is not None:
                length_test["max_value"] = field.maxLength
            column.setdefault("tests", []).append(
                {"dbt_expectations.expect_column_value_lengths_to_be_between": length_test}
            )
        if field.pii is not None:
            column.setdefault("meta", {})["pii"] = field.pii
        if field.classification is not None:
            column.setdefault("meta", {})["classification"] = field.classification
        if field.tags is not None and len(field.tags) > 0:
            column.setdefault("tags", []).extend(field.tags)
        if field.pattern is not None:
            # Beware, the data contract pattern is a regex, not a like pattern
            column.setdefault("tests", []).append(
                {"dbt_expectations.expect_column_values_to_match_regex": {"regex": field.pattern}}
            )
        if (
            field.minimum is not None
            or field.maximum is not None
            and field.exclusiveMinimum is None
            and field.exclusiveMaximum is None
        ):
            range_test = {}
            if field.minimum is not None:
                range_test["min_value"] = field.minimum
            if field.maximum is not None:
                range_test["max_value"] = field.maximum
            column.setdefault("tests", []).append({"dbt_expectations.expect_column_values_to_be_between": range_test})
        elif (
            field.exclusiveMinimum is not None
            or field.exclusiveMaximum is not None
            and field.minimum is None
            and field.maximum is None
        ):
            range_test = {}
            if field.exclusiveMinimum is not None:
                range_test["min_value"] = field.exclusiveMinimum
            if field.exclusiveMaximum is not None:
                range_test["max_value"] = field.exclusiveMaximum
            range_test["strictly"] = True
            column.setdefault("tests", []).append({"dbt_expectations.expect_column_values_to_be_between": range_test})
        else:
            if field.minimum is not None:
                column.setdefault("tests", []).append(
                    {"dbt_expectations.expect_column_values_to_be_between": {"min_value": field.minimum}}
                )
            if field.maximum is not None:
                column.setdefault("tests", []).append(
                    {"dbt_expectations.expect_column_values_to_be_between": {"max_value": field.maximum}}
                )
            if field.exclusiveMinimum is not None:
                column.setdefault("tests", []).append(
                    {
                        "dbt_expectations.expect_column_values_to_be_between": {
                            "min_value": field.exclusiveMinimum,
                            "strictly": True,
                        }
                    }
                )
            if field.exclusiveMaximum is not None:
                column.setdefault("tests", []).append(
                    {
                        "dbt_expectations.expect_column_values_to_be_between": {
                            "max_value": field.exclusiveMaximum,
                            "strictly": True,
                        }
                    }
                )

        # TODO: all constraints
        return column


class DBTSourceExporter(DBTExporter):
    def export(self, export_args) -> dict:
        self.dict_args = export_args  
        return self.to_dbt_sources_yaml(
            self.dict_args.get('data_contract'),
            self.dict_args.get('server')
            )

    def to_dbt_sources_yaml(self, data_contract_spec: DataContractSpecification, server: str = None, sql_type: str='snowflake'):
        source = {"name": data_contract_spec.id, "tables": []}
        dbt = {
            "version": 2,
            "sources": [source],
        }
        if data_contract_spec.info.owner is not None:
            source["meta"] = {"owner": data_contract_spec.info.owner}
        if data_contract_spec.info.description is not None:
            source["description"] = data_contract_spec.info.description
        found_server = data_contract_spec.servers.get(server)
        if found_server is not None:
            source["database"] = found_server.database
            source["schema"] = found_server.schema_

        for model_key, model_value in data_contract_spec.models.items():
            dbt_model = self._to_dbt_source_table(model_key, model_value, sql_type)
            source["tables"].append(dbt_model)
        return yaml.dump(dbt, indent=2, sort_keys=False, allow_unicode=True)


class DBTStageExporter(DBTExporter):
    def export(self, export_args) -> dict:
        self.dict_args = export_args  
        return self.to_dbt_staging_sql(
            self.dict_args.get('data_contract'),
            self.dict_args.get('model_name'),
            self.dict_args.get('model_value'), 
            )

    def to_dbt_staging_sql(self, data_contract_spec: DataContractSpecification, model_name: str, model_value: Model) -> str:
        if data_contract_spec.models is None or len(data_contract_spec.models.items()) != 1:
            
            print(
            "Export to dbt-staging-sql currently only works with exactly one model in the data contract."
            "Please specify the model name."
            )
            return ""

        id = data_contract_spec.id
        columns = [] 
        for field_name, field in model_value.fields.items():
            # TODO escape SQL reserved key words, probably dependent on server type
            columns.append(field_name)
        return f"""
        select 
            {", ".join(columns)}
        from {{{{ source('{id}', '{model_name}') }}}}
    """

 