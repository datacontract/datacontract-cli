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
	FieldName   *string
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

func CompareDatasets(old Dataset, new Dataset) []DatasetDifference {
	var result []DatasetDifference

	comparisons := []datasetComparison{
		checkIfModelWasRemoved,
	}

	for _, comparison := range comparisons {
		result = append(result, comparison(old, new)...)
	}

	return result
}

func checkIfModelWasRemoved(old Dataset, new Dataset) []DatasetDifference {
	var result []DatasetDifference

	for _, oldModel := range old.Models {
		found := false
		for _, newModel := range new.Models {
			if oldModel.Name == newModel.Name {
				found = true
				break
			}
		}

		if !found {
			result = append(result, DatasetDifference{
				Level:       DatasetDifferenceLevelModel,
				Severity:    DatasetDifferenceSeverityBreaking,
				ModelName:   oldModel.Name,
				FieldName:   nil,
				Description: fmt.Sprintf("model '%v' was removed", oldModel.Name),
			})
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

func modelsFromDbtSpecification(res dbtSpecification) []Model {
	var models []Model
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

func fieldsFromDbtModel(model dbtModel) []Field {
	var fields []Field
	for _, column := range model.Columns {
		fields = append(fields, Field{
			Name:        column.Name,
			Type:        &column.DataType,
			Description: &column.Description,
		})
	}
	return fields
}
