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

	FieldNameTermsNoticePeriod FieldName = "terms.noticePeriod"

	FieldNameSchemaType          FieldName = "schema.type"
	FieldNameSchemaSpecification FieldName = "schema.specification"
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

// todo:

func ValidateValue(value string, field SchemaField)  {
	panic("implement me")
}

// todo: links / additionalProperties
// todo: date
// todo: duration

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
	if startDate != nil && !hasDateFormat(startDate) {
		return &ValidationError{fieldName, ValidationErrorReasonIllegalFormat}
	}
	return nil
}

func hasDateFormat(startDate *string) bool {
	re := regexp.MustCompile("(\\d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12]\\d|3[01]))")
	return re.MatchString(*startDate)
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

// Terms

func ValidateTermsNoticePeriod(duration *string) *ValidationError {
	if duration != nil && !hasISO8601Format(*duration) {
		return &ValidationError{FieldNameTermsNoticePeriod, ValidationErrorReasonIllegalFormat}
	}
	return nil
}

func hasISO8601Format(duration string) bool {
	re := regexp.MustCompile(`^P(?:\d+Y)?(?:\d+M)?(?:\d+W)?(?:\d+D)?(?:T(?:\d+H)?(?:\d+M)?(?:\d+S)?)?$`)
	return re.MatchString(duration)
}

// Schema

func ValidateSchemaType(schemaType string) *ValidationError {
	return validateStringNotEmpty(schemaType, FieldNameSchemaType)
}

func ValidateSchemaSpecification(specification string) *ValidationError {
	return validateStringNotEmpty(specification, FieldNameSchemaSpecification)
}

// common

func validateStringNotEmpty(value string, fieldName FieldName) *ValidationError {
	if value == "" {
		return &ValidationError{fieldName, ValidationErrorReasonEmptyString}
	}
	return nil
}
