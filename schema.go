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
	Level       DatasetDifferenceLevel
	Severity    DatasetDifferenceSeverity
	ModelName   string
	FieldName   string
	Description string
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
		modelWasRemoved,
		fieldWasRemoved,
	}

	for _, comparison := range comparisons {
		result = append(result, comparison(old, new)...)
	}

	return result
}

func modelWasRemoved(old, new Dataset) (result []DatasetDifference) {
	for _, oldModel := range old.Models {
		if oldModel.findEquivalent(new.Models) == nil {
			result = append(result, DatasetDifference{
				Level:       DatasetDifferenceLevelModel,
				Severity:    DatasetDifferenceSeverityBreaking,
				ModelName:   oldModel.Name,
				Description: fmt.Sprintf("model '%v' was removed", oldModel.Name),
			})
		}
	}

	return result
}

func fieldWasRemoved(old, new Dataset) (result []DatasetDifference) {
	var difference fieldEquivalentExistsNot = func(
		modelName string,
		fieldName string,
		field Field,
	) DatasetDifference {
		return DatasetDifference{
			Level:       DatasetDifferenceLevelField,
			Severity:    DatasetDifferenceSeverityBreaking,
			ModelName:   modelName,
			FieldName:   fieldName,
			Description: fmt.Sprintf("field '%v.%v' was removed", modelName, fieldName),
		}
	}

	return append(result, compareFields(old, new, nil, &difference)...)
}

type fieldEquivalentExists func(
	modelName string,
	prefixedFieldName string,
	oldField Field,
	newField Field,
) DatasetDifference

type fieldEquivalentExistsNot func(
	modelName string,
	prefixedFieldName string,
	field Field,
) DatasetDifference

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

		if newField := oldField.findEquivalent(newFields); newField == nil && whenEquivalentExistsNot != nil {
			result = append(result, (*whenEquivalentExistsNot)(modelName, fieldName, oldField))
		} else {
			if whenEquivalentExists != nil {
				result = append(result, (*whenEquivalentExists)(modelName, fieldName, oldField, *newField))
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
