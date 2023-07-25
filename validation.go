package main

import (
	"fmt"
)

type FieldName string

const (
	FieldNameDataContractSpecification FieldName = "dataContractSpecification"
)

type ValidationErrorReason string

const (
	ValidationErrorReasonEmptyString  ValidationErrorReason = "Empty string"
	ValidationErrorReasonIllegalValue ValidationErrorReason = "Illegal value"
)

type ValidationError struct {
	Field  FieldName
	Reason ValidationErrorReason
}

func (e *ValidationError) Error() string {
	return fmt.Sprintf("Validation error for field '%v': %v.", e.Field, e.Reason)
}

func ValidateDataContractSpecification(dataContractSpecification string) *ValidationError {
	if dataContractSpecification == "" {
		return &ValidationError{FieldNameDataContractSpecification, ValidationErrorReasonEmptyString}
	}
	if dataContractSpecification != "0.0.1" {
		return &ValidationError{FieldNameDataContractSpecification, ValidationErrorReasonIllegalValue}
	}
	return nil
}
