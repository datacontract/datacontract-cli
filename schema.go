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

type datasetComparison = func(old Dataset, new Dataset) []DatasetDifference

func CompareDatasets(old Dataset, new Dataset) (result []DatasetDifference) {
	comparisons := []datasetComparison{
		modelWasRemoved,
		fieldWasRemoved,
	}

	for _, comparison := range comparisons {
		result = append(result, comparison(old, new)...)
	}

	return result
}

func modelWasRemoved(old Dataset, new Dataset) (result []DatasetDifference) {
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

func fieldWasRemoved(old Dataset, new Dataset) (result []DatasetDifference) {
	for _, oldModel := range old.Models {
		if newModel := oldModel.findEquivalent(new.Models); newModel != nil {
			result = append(result,
				fieldWasRemovedRecursive(oldModel.Name, nil, oldModel.Fields, newModel.Fields)...)
		}
	}

	return result
}

func fieldWasRemovedRecursive(
	modelName string,
	prefix *string,
	oldFields, newFields []Field,
) (result []DatasetDifference) {
	for _, oldField := range oldFields {
		var fieldName string
		if prefix == nil {
			fieldName = oldField.Name
		} else {
			fieldName = fmt.Sprintf("%v.%v", *prefix, oldField.Name)
		}

		if newField := oldField.findEquivalent(newFields); newField == nil {
			result = append(result, DatasetDifference{
				Level:       DatasetDifferenceLevelField,
				Severity:    DatasetDifferenceSeverityBreaking,
				ModelName:   modelName,
				FieldName:   fieldName,
				Description: fmt.Sprintf("field '%v.%v' was removed", modelName, fieldName),
			})
		} else {
			result = append(result,
				fieldWasRemovedRecursive(modelName, &fieldName, oldField.Fields, newField.Fields)...)
		}
	}
	return result
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
