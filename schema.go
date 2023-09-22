package main

import (
	"fmt"
	"gopkg.in/yaml.v3"
)

type Dataset struct {
	SchemaType string
	Models     []Model
}

type Model struct {
	Name        string
	Type        *string
	Description *string
	Fields      []Field
}

type Field struct {
	Name                  string
	Type                  *string
	Description           *string
	Required              bool
	Unique                bool
	AdditionalConstraints []FieldConstraint
	Fields                []Field
}

type FieldConstraint struct {
	Type       string
	Expression string
}

type DatasetDifference struct {
	Type        DatasetDifferenceType
	Level       DatasetDifferenceLevel
	Severity    DatasetDifferenceSeverity
	ModelName   *string
	FieldName   string
	Description string
}

type DatasetDifferenceType int

const (
	DatasetDifferenceTypeModelRemoved DatasetDifferenceType = iota
	DatasetDifferenceTypeFieldRemoved
	DatasetDifferenceTypeFieldTypeChanged
	DatasetDifferenceTypeFieldRequirementRemoved
	DatasetDifferenceTypeFieldUniquenessRemoved
	DatasetDifferenceTypeFieldAdditionalConstraintAdded
	DatasetDifferenceTypeFieldAdditionalConstraintRemoved
	DatasetDifferenceDatasetSchemaTypeChanged
	DatasetDifferenceModelAdded
)

func (d DatasetDifferenceType) String() string {
	switch d {
	// breaking
	case DatasetDifferenceTypeModelRemoved:
		return "model-removed"
	case DatasetDifferenceTypeFieldRemoved:
		return "field-removed"
	case DatasetDifferenceTypeFieldTypeChanged:
		return "field-type-changed"
	case DatasetDifferenceTypeFieldRequirementRemoved:
		return "field-requirement-removed"
	case DatasetDifferenceTypeFieldUniquenessRemoved:
		return "field-uniqueness-removed"
	case DatasetDifferenceTypeFieldAdditionalConstraintRemoved:
		return "field-constraint-removed"
	case DatasetDifferenceTypeFieldAdditionalConstraintAdded:
		return "field-constraint-added"
	// info
	case DatasetDifferenceDatasetSchemaTypeChanged:
		return "dataset-schema-type-changed"
	case DatasetDifferenceModelAdded:
		return "model-added"
	}

	return ""
}

type DatasetDifferenceLevel int

const (
	DatasetDifferenceLevelDataset DatasetDifferenceLevel = iota
	DatasetDifferenceLevelModel
	DatasetDifferenceLevelField
)

func (d DatasetDifferenceLevel) String() string {
	switch d {
	case DatasetDifferenceLevelDataset:
		return "dataset"
	case DatasetDifferenceLevelModel:
		return "model"
	case DatasetDifferenceLevelField:
		return "field"
	}

	return ""
}

type DatasetDifferenceSeverity int

const (
	DatasetDifferenceSeverityInfo DatasetDifferenceSeverity = iota
	DatasetDifferenceSeverityBreaking
)

func (d DatasetDifferenceSeverity) String() string {
	switch d {
	case DatasetDifferenceSeverityInfo:
		return "info"
	case DatasetDifferenceSeverityBreaking:
		return "breaking"
	}

	return ""
}

type datasetComparison = func(old, new Dataset) []DatasetDifference

func CompareDatasets(old, new Dataset) (result []DatasetDifference) {
	comparisons := []datasetComparison{
		// breaking
		modelRemoved,
		fieldRemoved,
		fieldTypeChanged,
		fieldRequirementRemoved,
		fieldUniquenessRemoved,
		fieldConstraintAdded,
		fieldConstraintRemoved,
		// info
		datasetSchemaTypeChanged,
		modelAdded,
	}

	for _, comparison := range comparisons {
		result = append(result, comparison(old, new)...)
	}

	return result
}

func modelRemoved(old, new Dataset) (result []DatasetDifference) {
	for _, oldModel := range old.Models {
		if oldModel.findEquivalent(new.Models) == nil {
			result = append(result, DatasetDifference{
				Type:        DatasetDifferenceTypeModelRemoved,
				Level:       DatasetDifferenceLevelModel,
				Severity:    DatasetDifferenceSeverityBreaking,
				ModelName:   &oldModel.Name,
				Description: fmt.Sprintf("model '%v' was removed", oldModel.Name),
			})
		}
	}

	return result
}

func fieldRemoved(old, new Dataset) (result []DatasetDifference) {
	var difference fieldEquivalentExistsNot = func(
		modelName, fieldName string,
		field Field,
	) (result []DatasetDifference) {
		return append(result, DatasetDifference{
			Type:        DatasetDifferenceTypeFieldRemoved,
			Level:       DatasetDifferenceLevelField,
			Severity:    DatasetDifferenceSeverityBreaking,
			ModelName:   &modelName,
			FieldName:   fieldName,
			Description: fmt.Sprintf("field '%v.%v' was removed", modelName, fieldName),
		})
	}

	return append(result, compareFields(old, new, nil, &difference)...)
}

func fieldTypeChanged(old, new Dataset) (result []DatasetDifference) {
	var difference fieldEquivalentExists = func(
		modelName, fieldName string,
		oldField, newField Field,
	) (result []DatasetDifference) {
		if !equalStringPointers(oldField.Type, newField.Type) {
			return append(result, DatasetDifference{
				Type:      DatasetDifferenceTypeFieldTypeChanged,
				Level:     DatasetDifferenceLevelField,
				Severity:  DatasetDifferenceSeverityBreaking,
				ModelName: &modelName,
				FieldName: fieldName,
				Description: fmt.Sprintf(
					"type of field '%v.%v' was changed from '%v' to '%v'",
					modelName,
					fieldName,
					stringPointerString(oldField.Type),
					stringPointerString(newField.Type),
				),
			})
		} else {
			return result
		}
	}

	return append(result, compareFields(old, new, &difference, nil)...)
}

func fieldRequirementRemoved(old, new Dataset) (result []DatasetDifference) {
	var difference fieldEquivalentExists = func(
		modelName, fieldName string,
		oldField, newField Field,
	) (result []DatasetDifference) {
		if oldField.Required && !newField.Required {
			return append(result, DatasetDifference{
				Type:        DatasetDifferenceTypeFieldRequirementRemoved,
				Level:       DatasetDifferenceLevelField,
				Severity:    DatasetDifferenceSeverityBreaking,
				ModelName:   &modelName,
				FieldName:   fieldName,
				Description: fmt.Sprintf("field requirement of '%v.%v' was removed", modelName, fieldName),
			})
		} else {
			return result
		}
	}

	return append(result, compareFields(old, new, &difference, nil)...)
}

func fieldUniquenessRemoved(old, new Dataset) (result []DatasetDifference) {
	var difference fieldEquivalentExists = func(
		modelName, fieldName string,
		oldField, newField Field,
	) (result []DatasetDifference) {
		if oldField.Unique && !newField.Unique {
			return append(result, DatasetDifference{
				Type:        DatasetDifferenceTypeFieldUniquenessRemoved,
				Level:       DatasetDifferenceLevelField,
				Severity:    DatasetDifferenceSeverityBreaking,
				ModelName:   &modelName,
				FieldName:   fieldName,
				Description: fmt.Sprintf("field uniqueness of '%v.%v' was removed", modelName, fieldName),
			})
		} else {
			return result
		}
	}

	return append(result, compareFields(old, new, &difference, nil)...)
}

func fieldConstraintAdded(old, new Dataset) (result []DatasetDifference) {
	var difference fieldEquivalentExists = func(
		modelName, fieldName string,
		oldField, newField Field,
	) (result []DatasetDifference) {
		for _, constraint := range newField.AdditionalConstraints {
			if !constraint.isIn(oldField.AdditionalConstraints) {
				result = append(result, DatasetDifference{
					Type:      DatasetDifferenceTypeFieldAdditionalConstraintAdded,
					Level:     DatasetDifferenceLevelField,
					Severity:  DatasetDifferenceSeverityBreaking,
					ModelName: &modelName,
					FieldName: fieldName,
					Description: fmt.Sprintf("field constraint (%v: %v) of '%v.%v' was added",
						constraint.Type, constraint.Expression, modelName, fieldName),
				})
			}
		}

		return result
	}

	return append(result, compareFields(old, new, &difference, nil)...)
}

func fieldConstraintRemoved(old, new Dataset) (result []DatasetDifference) {
	var difference fieldEquivalentExists = func(
		modelName, fieldName string,
		oldField, newField Field,
	) (result []DatasetDifference) {
		for _, constraint := range oldField.AdditionalConstraints {
			if !constraint.isIn(newField.AdditionalConstraints) {
				result = append(result, DatasetDifference{
					Type:      DatasetDifferenceTypeFieldAdditionalConstraintRemoved,
					Level:     DatasetDifferenceLevelField,
					Severity:  DatasetDifferenceSeverityBreaking,
					ModelName: &modelName,
					FieldName: fieldName,
					Description: fmt.Sprintf("field constraint (%v: %v) of '%v.%v' was removed",
						constraint.Type, constraint.Expression, modelName, fieldName),
				})
			}
		}

		return result
	}

	return append(result, compareFields(old, new, &difference, nil)...)
}

func datasetSchemaTypeChanged(old, new Dataset) (result []DatasetDifference) {
	if old.SchemaType != new.SchemaType {
		result = append(result, DatasetDifference{
			Type:        DatasetDifferenceDatasetSchemaTypeChanged,
			Level:       DatasetDifferenceLevelDataset,
			Severity:    DatasetDifferenceSeverityInfo,
			Description: fmt.Sprintf("schema type changed from '%v' to '%v'", old.SchemaType, new.SchemaType),
		})
	}
	return result
}

func modelAdded(old, new Dataset) (result []DatasetDifference) {
	for _, newModel := range new.Models {
		if newModel.findEquivalent(old.Models) == nil {
			result = append(result, DatasetDifference{
				Type:        DatasetDifferenceModelAdded,
				Level:       DatasetDifferenceLevelModel,
				Severity:    DatasetDifferenceSeverityInfo,
				ModelName:   &newModel.Name,
				Description: fmt.Sprintf("model '%v' was added", newModel.Name),
			})
		}
	}

	return result
}

func (constraint FieldConstraint) isIn(list []FieldConstraint) bool {
	for _, oldConstraint := range list {
		if constraint.Type == oldConstraint.Type && constraint.Expression == oldConstraint.Expression {
			return true
		}
	}

	return false
}

func equalStringPointers(s1, s2 *string) bool {
	// both are the same (e.g. nil)
	if s1 == s2 {
		return true
	}

	// one pointer is nil, the other not
	if (s1 == nil && s2 != nil) || (s1 != nil && s2 == nil) {
		return false
	}

	return *s1 == *s2
}

type fieldEquivalentExists func(
	modelName string,
	prefixedFieldName string,
	oldField Field,
	newField Field,
) []DatasetDifference

type fieldEquivalentExistsNot func(
	modelName string,
	prefixedFieldName string,
	field Field,
) []DatasetDifference

func compareFields(
	old Dataset,
	new Dataset,
	whenEquivalentExists *fieldEquivalentExists,
	whenEquivalentExistsNot *fieldEquivalentExistsNot,
) (result []DatasetDifference) {
	for _, oldModel := range old.Models {
		if newModel := oldModel.findEquivalent(new.Models); newModel != nil {
			result = append(
				result,
				compareFieldsRecursive(
					oldModel.Fields,
					newModel.Fields,
					oldModel.Name,
					nil,
					whenEquivalentExists,
					whenEquivalentExistsNot,
				)...,
			)
		}
	}

	return result
}

// traverse through fields and their subfields
// apply corresponding methods if equivalent field exists or not
func compareFieldsRecursive(
	oldFields, newFields []Field,
	modelName string,
	fieldPrefix *string,
	whenEquivalentExists *fieldEquivalentExists,
	whenEquivalentExistsNot *fieldEquivalentExistsNot,
) (result []DatasetDifference) {
	for _, oldField := range oldFields {
		fieldName := oldField.prefixedName(fieldPrefix)

		if newField := oldField.findEquivalent(newFields); newField == nil {
			if whenEquivalentExistsNot != nil {
				result = append(result, (*whenEquivalentExistsNot)(modelName, fieldName, oldField)...)
			}
		} else {
			if whenEquivalentExists != nil {
				result = append(result, (*whenEquivalentExists)(modelName, fieldName, oldField, *newField)...)
			}
			result = append(result,
				compareFieldsRecursive(
					oldField.Fields,
					newField.Fields,
					modelName,
					&fieldName,
					whenEquivalentExists,
					whenEquivalentExistsNot,
				)...)
		}
	}
	return result
}

func (field Field) prefixedName(prefix *string) string {
	var fieldName string
	if prefix == nil {
		fieldName = field.Name
	} else {
		fieldName = fmt.Sprintf("%v.%v", *prefix, field.Name)
	}
	return fieldName
}

func (model Model) findEquivalent(otherModels []Model) (result *Model) {
	for _, newModel := range otherModels {
		if model.Name == newModel.Name {
			result = &newModel
			break
		}
	}
	return result
}

func (field Field) findEquivalent(otherFields []Field) (result *Field) {
	for _, newField := range otherFields {
		if field.Name == newField.Name {
			result = &newField
			break
		}
	}
	return result
}

func ParseDataset(schemaType string, specification []byte) (*Dataset, error) {
	switch schemaType {
	case "dbt":
		return parseDbtDataset(specification), nil
	default:
		return nil, fmt.Errorf("unknown schema type %v", schemaType)
	}
}

// dbt

type dbtSpecification struct {
	Models []dbtModel
}

type dbtModel struct {
	Name        string
	Description string
	Config      dbtModelConfig
	Constraints []dbtConstraint
	Columns     []dbtColumn
}

type dbtConstraint struct {
	Type       string
	Expression string
	Columns    []string
}

type dbtModelConfig struct {
	Materialized string
}

type dbtColumn struct {
	Name        string
	Description string
	DataType    string `yaml:"data_type"`
	Constraints []dbtConstraint
}

func parseDbtDataset(specification []byte) *Dataset {
	var res dbtSpecification

	yaml.Unmarshal(specification, &res)
	models := modelsFromDbtSpecification(res)

	return &Dataset{SchemaType: "dbt", Models: models}
}

func modelsFromDbtSpecification(res dbtSpecification) (models []Model) {
	for _, model := range res.Models {
		models = append(models, Model{
			Name:        model.Name,
			Type:        &model.Config.Materialized,
			Description: &model.Description,
			Fields:      fieldsFromDbtModel(model),
		})
	}

	return models
}

func fieldsFromDbtModel(model dbtModel) (fields []Field) {
	for _, column := range model.Columns {
		allDbtConstraints := combineDbtConstraints(model, column)

		fields = append(fields, Field{
			Name:                  column.Name,
			Type:                  &column.DataType,
			Description:           &column.Description,
			Required:              containsDbtConstraint(allDbtConstraints, "not_null"),
			Unique:                containsDbtConstraint(allDbtConstraints, "unique"),
			AdditionalConstraints: additionalDbtConstraints(allDbtConstraints),
		})
	}

	return fields
}

func combineDbtConstraints(model dbtModel, column dbtColumn) (result []dbtConstraint) {
	for _, constraint := range model.Constraints {
		for _, columnName := range constraint.Columns {
			if columnName == column.Name {
				result = append(result, constraint)
			}
		}
	}

	for _, constraint := range column.Constraints {
		result = append(result, constraint)
	}

	return result
}

func containsDbtConstraint(constraints []dbtConstraint, constraintType string) bool {
	for _, constraint := range constraints {
		if constraint.Type == constraintType {
			return true
		}
	}

	return false
}

func additionalDbtConstraints(allDbtConstraints []dbtConstraint) (result []FieldConstraint) {
	for _, constraint := range allDbtConstraints {
		if constraint.Type != "not_null" && constraint.Type != "unique" {
			result = append(result,
				FieldConstraint{Type: constraint.Type, Expression: constraint.Expression})
		}
	}

	return result
}

func stringPointerString(str *string) string {
	if str == nil {
		return ""
	}

	return *str
}
