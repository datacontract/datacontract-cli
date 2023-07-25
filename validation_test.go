package main

import (
	"testing"
)

func TestValidateDataContractSpecification_HappyCase(t *testing.T) {
	e := ValidateDataContractSpecification("0.0.1")
	assertPassed(t, e)
}

func TestValidateDataContractSpecification_Unknown(t *testing.T) {
	e := ValidateDataContractSpecification("0.0.2")
	assertFailed(t, e, FieldNameDataContractSpecification, ValidationErrorReasonIllegalValue)
}

func TestValidateDataContractSpecification_Empty(t *testing.T) {
	e := ValidateDataContractSpecification("")
	assertFailed(t, e, FieldNameDataContractSpecification, ValidationErrorReasonEmptyString)
}

func assertPassed(t *testing.T, e *ValidationError) {
	if e != nil {
		t.Error("Must pass.")
	}
}

func assertFailed(t *testing.T, e *ValidationError, field FieldName, reason ValidationErrorReason) {
	if e == nil {
		t.Error("Must fail.")
	}
	if e == nil || e.Field != field {
		t.Errorf("Field name must be '%v'", field)
	}
	if e == nil || e.Reason != reason {
		t.Errorf("Validation error reason must be '%v'", reason)
	}
}
