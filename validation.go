package main

import (
	"fmt"
	"regexp"
)

type FieldName string

const (
	FieldNameDataContractSpecification FieldName = "dataContractSpecification"
	FieldNameInfoId                    FieldName = "info.id"
	FieldNameInfoStartDate             FieldName = "info.startDate"
	FieldNameInfoEndDate               FieldName = "info.endDate"
)

type ValidationErrorReason string

const (
	ValidationErrorReasonEmptyString   ValidationErrorReason = "Empty string"
	ValidationErrorReasonIllegalValue  ValidationErrorReason = "Illegal value"
	ValidationErrorReasonIllegalFormat ValidationErrorReason = "Illegal format"
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

func ValidateInfoId(id string) *ValidationError {
	if id == "" {
		return &ValidationError{FieldNameInfoId, ValidationErrorReasonEmptyString}
	}
	return nil
}

func ValidateInfoStartDate(startDate *string) *ValidationError {
	return validateDateFormat(FieldNameInfoStartDate, startDate)
}

func ValidateInfoEndDate(endDate *string) *ValidationError {
	return validateDateFormat(FieldNameInfoEndDate, endDate)
}

func validateDateFormat(fieldName FieldName, startDate *string) *ValidationError {
	if startDate != nil {
		hasDateFormat, _ := hasDateFormat(startDate)
		if !hasDateFormat {
			return &ValidationError{fieldName, ValidationErrorReasonIllegalFormat}
		}
	}
	return nil
}

func hasDateFormat(startDate *string) (bool, error) {
	return regexp.MatchString("(\\d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12]\\d|3[01]))", *startDate)
}
