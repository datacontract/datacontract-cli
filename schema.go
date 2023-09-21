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

func parseDataset(schemaType string, specification []byte) (*Dataset, error) {
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
