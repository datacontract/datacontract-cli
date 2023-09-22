package main

import (
	"fmt"
	"gopkg.in/yaml.v3"
)

type Dataset struct {
	Models []Model
}

type Model struct {
	Name        string
	Type        *string
	Description *string
	Fields      []Field
}

type Field struct {
	Name        string
	Type        *string
	Description *string
	Fields      []Field
}

type DatasetDifference struct {
	Type        DatasetDifferenceType
	Level       DatasetDifferenceLevel
	Severity    DatasetDifferenceSeverity
	ModelName   string
	FieldName   string
	Description string
}

type DatasetDifferenceType int

const (
	DatasetDifferenceTypeModelRemoved DatasetDifferenceType = iota
	DatasetDifferenceTypeFieldRemoved
	DatasetDifferenceTypeFieldTypeChanged
)

func (d DatasetDifferenceType) String() string {
	switch d {
	case DatasetDifferenceTypeModelRemoved:
		return "model-removed"
	case DatasetDifferenceTypeFieldRemoved:
		return "field-removed"
	case DatasetDifferenceTypeFieldTypeChanged:
		return "field-type-changed"
	}
	return ""
}

type DatasetDifferenceLevel int

const (
	DatasetDifferenceLevelModel DatasetDifferenceLevel = iota
	DatasetDifferenceLevelField
)

func (d DatasetDifferenceLevel) String() string {
	switch d {
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
		modelRemoved,
		fieldRemoved,
		fieldTypeChanged,
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
				ModelName:   oldModel.Name,
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
	) *DatasetDifference {
		return &DatasetDifference{
			Type:        DatasetDifferenceTypeFieldRemoved,
			Level:       DatasetDifferenceLevelField,
			Severity:    DatasetDifferenceSeverityBreaking,
			ModelName:   modelName,
			FieldName:   fieldName,
			Description: fmt.Sprintf("field '%v.%v' was removed", modelName, fieldName),
		}
	}

	return append(result, compareFields(old, new, nil, &difference)...)
}

func fieldTypeChanged(old, new Dataset) (result []DatasetDifference) {
	var difference fieldEquivalentExists = func(
		modelName, fieldName string,
		oldField, newField Field,
	) *DatasetDifference {
		if !equalStringPointers(oldField.Type, newField.Type) {
			return &DatasetDifference{
				Type:      DatasetDifferenceTypeFieldTypeChanged,
				Level:     DatasetDifferenceLevelField,
				Severity:  DatasetDifferenceSeverityBreaking,
				ModelName: modelName,
				FieldName: fieldName,
				Description: fmt.Sprintf(
					"type of field '%v.%v' was changed from %v to %v",
					modelName,
					fieldName,
					*oldField.Type,
					*newField.Type,
				),
			}
		} else {
			return nil
		}
	}

	return append(result, compareFields(old, new, &difference, nil)...)
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
) *DatasetDifference

type fieldEquivalentExistsNot func(
	modelName string,
	prefixedFieldName string,
	field Field,
) *DatasetDifference

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
				difference := (*whenEquivalentExistsNot)(modelName, fieldName, oldField)
				if difference != nil {
					result = append(result, *difference)
				}
			}
		} else {
			if whenEquivalentExists != nil {
				difference := (*whenEquivalentExists)(modelName, fieldName, oldField, *newField)
				if difference != nil {
					result = append(result, *difference)
				}
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
	Columns     []dbtColumn
}

type dbtModelConfig struct {
	Materialized string
}

type dbtColumn struct {
	Name        string
	Description string
	DataType    string `yaml:"data_type"`
}

func parseDbtDataset(specification []byte) *Dataset {
	var res dbtSpecification

	yaml.Unmarshal(specification, &res)
	models := modelsFromDbtSpecification(res)

	return &Dataset{models}
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
		fields = append(fields, Field{
			Name:        column.Name,
			Type:        &column.DataType,
			Description: &column.Description,
		})
	}
	return fields
}
