package main

import (
	"fmt"
	"regexp"
)

type FieldName string

const (
	FieldNameDataContractSpecification FieldName = "dataContractSpecification"

	FieldNameInfoId        FieldName = "info.id"
	FieldNameInfoStartDate FieldName = "info.startDate"
	FieldNameInfoEndDate   FieldName = "info.endDate"

	FieldNameProviderTeamId        FieldName = "provider.teamId"
	FieldNameProviderDataProductId FieldName = "provider.dataProductId"
	FieldNameProviderOutputPortId  FieldName = "provider.outputPortId"

	FieldNameConsumerTeamId FieldName = "consumer.teamId"
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
	emptyStringError :=
		validateStringNotEmpty(dataContractSpecification, FieldNameDataContractSpecification)
	if emptyStringError != nil {
		return emptyStringError
	}
	if dataContractSpecification != "0.0.1" {
		return &ValidationError{FieldNameDataContractSpecification, ValidationErrorReasonIllegalValue}
	}
	return nil
}

// Info

func ValidateInfoId(id string) *ValidationError {
	return validateStringNotEmpty(id, FieldNameInfoId)
}

func ValidateInfoStartDate(startDate *string) *ValidationError {
	return validateOptionalDate(FieldNameInfoStartDate, startDate)
}

func ValidateInfoEndDate(endDate *string) *ValidationError {
	return validateOptionalDate(FieldNameInfoEndDate, endDate)
}

func validateOptionalDate(fieldName FieldName, startDate *string) *ValidationError {
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

// Provider

func ValidateProviderTeamId(teamId string) *ValidationError {
	return validateStringNotEmpty(teamId, FieldNameProviderTeamId)
}

func ValidateProviderDataProductId(dataProductId string) *ValidationError {
	return validateStringNotEmpty(dataProductId, FieldNameProviderDataProductId)
}

func ValidateProviderOutputPortId(outputPortId string) *ValidationError {
	return validateStringNotEmpty(outputPortId, FieldNameProviderOutputPortId)
}

// Consumer

func ValidateConsumerTeamId(teamId string) *ValidationError {
	return validateStringNotEmpty(teamId, FieldNameConsumerTeamId)
}

// common

func validateStringNotEmpty(value string, fieldName FieldName) *ValidationError {
	if value == "" {
		return &ValidationError{fieldName, ValidationErrorReasonEmptyString}
	}
	return nil
}
