from ..lint import Linter, LinterResult
from datacontract.model.data_contract_specification import\
    DataContractSpecification, Model


class ValidFieldConstraintsLinter(Linter):
    """Check validity of field constraints.

      More precisely, check that only numeric constraints are specified on fields
      of numeric type and string constraints on fields of string type.
    """

    valid_types_for_constraint = {
        "pattern": set(["string", "text", "varchar"]),
        "format": set(["string", "text", "varchar"]),
        "minLength": set(["string", "text", "varchar"]),
        "maxLength": set(["string", "text", "varchar"]),
        "minimum": set(["int", "integer", "number", "decimal", "numeric",
                        "long", "bigint", "float", "double"]),
        "exclusiveMinimum": set(["int", "integer", "number", "decimal", "numeric",
                                 "long", "bigint", "float", "double"]),
        "maximum": set(["int", "integer", "number", "decimal", "numeric",
                        "long", "bigint", "float", "double"]),
        "exclusiveMaximum": set(["int", "integer", "number", "decimal", "numeric",
                                 "long", "bigint", "float", "double"]),
    }

    @property
    def name(self):
        return "Fields use valid constraints"

    def lint_implementation(
            self,
            contract: DataContractSpecification
    ) -> LinterResult:
        result = LinterResult()
        for (model_name, model) in contract.models.items():
            for (field_name, field) in model.fields.items():
                for (_property, allowed_types) in self.valid_types_for_constraint.items():
                    if _property in field.model_fields_set and field.type not in allowed_types:
                        result = result.with_error(
                            f"Forbidden constraint '{_property}' defined on field "
                            f"'{field_name}' in model '{model_name}'. Field type "
                            f"is '{field.type}'.")
        return result
