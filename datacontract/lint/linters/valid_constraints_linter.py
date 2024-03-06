from ..lint import Linter, LinterResult
from datacontract.model.data_contract_specification import\
    DataContractSpecification, Field


class ValidFieldConstraintsLinter(Linter):
    """Check validity of field constraints.

      More precisely, check that only numeric constraints are specified on
      fields of numeric type and string constraints on fields of string type.
      Additionally, the linter checks that defined constraints make sense.
      Minimum values should not be greater than maximum values, exclusive and
      non-exclusive minimum and maximum should not be combined and string
      pattern and format should not be combined.

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

    def check_minimum_maximum(self, field: Field, field_name: str, model_name: str) -> LinterResult:
        match (field.minimum, field.maximum, field.exclusiveMinimum, field.exclusiveMaximum):
            case (_min, _max, None, None) if _min > _max:
                return LinterResult.erroneous(
                    f"Minimum {_min} is greater than maximum {_max} on "
                    f"field '{field_name}' in model '{model_name}'.")
            case (None, None, _min, _max) if _min >= max:
                return LinterResult.erroneous(
                    f"Exclusive minimum {_min} is greater than exclusive"
                    f" maximum {_max} on field '{field_name}' in model '{model_name}'.")
            case (_min, _max, _xmin, _xmax):
                return LinterResult.erroneous(
                    f"Both exclusive minimum and exclusive maximum are "
                    f"defined on field '{field_name}' in model '{model_name}'.")
            case (_min, None, _xmin, None):
                return LinterResult.erroneous(
                    f"Both exclusive and non-exclusive minimum are "
                    f"defined on field '{field_name}' in model '{model_name}'.")
            case (None, _max, None, _xmax):
                return LinterResult.erroneous(
                    f"Both exclusive and non-exclusive minimum are "
                    f"defined on field '{field_name}' in model '{model_name}'.")
        return LinterResult()

    def check_string_constraints(self, field: Field, field_name: str, model_name: str) -> LinterResult:
        result = LinterResult()
        if field.minLength and field.maxLength and field.minLength > field.maxLength:
            result = result.with_error(
                f"Minimum length is greater that maximum length on"
                f" field '{field_name}' in model '{model_name}'.")
        if field.pattern and field.format:
            result = result.with_error(
                f"Both a pattern and a format are defined for field"
                f" '{field_name}' in model '{model_name}'.")
        return result

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
                result = result.combine(self.check_minimum_maximum(field, field_name, model_name))
                result = result.combine(self.check_string_constraints(field, field_name, model_name))
        return result
