package datacontract

import (
	"fmt"
	"gopkg.in/yaml.v3"
)

func GetModelSpecificationFromSchema(dataContract DataContract, pathToType []string, pathToSpecification []string) (*InternalModelSpecification, error) {
	schemaType, schemaSpecification, err := extractSchemaSpecification(dataContract, pathToType, pathToSpecification)
	if err != nil {
		// ignore if no schema found
		return nil, nil
	}

	schemaSpecificationBytes := TakeStringOrMarshall(schemaSpecification)
	parsedDataset := ParseSchema(schemaType, schemaSpecificationBytes)

	return &parsedDataset, err
}

func extractSchemaSpecification(
	contract DataContract,
	pathToType []string,
	pathToSpecification []string,
) (schemaType string, specification any, err error) {
	schemaType, err = getSchemaType(contract, pathToType)
	if err != nil {
		return "", nil, fmt.Errorf("can't get schema type: %w", err)
	}

	specification, err = getSpecification(contract, pathToSpecification)
	if err != nil {
		return schemaType, nil, fmt.Errorf("can't get schema specification: %w", err)
	}

	return schemaType, specification, nil
}

func getSchemaType(contract DataContract, path []string) (schemaType string, err error) {
	schemaTypeUntyped, err := GetValue(contract, path)
	if err != nil {
		return "", fmt.Errorf("can't get value of schema type for path %v: %w", path, err)
	}

	schemaType, ok := schemaTypeUntyped.(string)
	if !ok {
		return "", fmt.Errorf("schema type not a string")
	}

	return schemaType, nil
}

func getSpecification(contract DataContract, path []string) (specification any, err error) {
	specification, err = GetValue(contract, path)
	if err != nil {
		return nil, fmt.Errorf("can't get value of schema specification for path %v: %w", path, err)
	}

	return specification, nil
}

func ParseSchema(schemaType string, specification []byte) InternalModelSpecification {
	switch schemaType {
	case "dbt":
		return parseDbtDataset(specification)
	default:
		return InternalModelSpecification{}
	}
}

func CreateSchema(schemaType string, specification InternalModelSpecification) ([]byte, error) {
	switch schemaType {
	case "dbt":
		return createDbtSpecification(specification)
	default:
		return nil, nil
	}
}

// dbt

func createDbtSpecification(specification InternalModelSpecification) ([]byte, error) {
	dbtSpecification := dbtSpecification{}
	dbtSpecification.Models = createDbtModels(specification)

	return yaml.Marshal(dbtSpecification)
}

func createDbtModels(specification InternalModelSpecification) []dbtModel {
	var dbtModels []dbtModel

	for _, model := range specification.Models {
		dbtModels = append(dbtModels, createDbtModel(model))
	}

	return dbtModels
}

func createDbtModel(model InternalModel) dbtModel {
	dbtModel := dbtModel{
		Name:    model.Name,
		Columns: createDbtColumns(model.Fields),
	}

	if model.Description != nil {
		dbtModel.Description = *model.Description
	}

	if model.Type != nil {
		dbtModel.Config = dbtModelConfig{
			Materialized: *model.Type,
		}
	}

	return dbtModel
}

func createDbtColumns(internalModelFields []InternalField) []dbtColumn {
	var columns []dbtColumn
	for _, field := range internalModelFields {
		columns = append(columns, createDbtColumn(field))
	}
	return columns
}

func createDbtColumn(field InternalField) dbtColumn {
	dbtColumn := dbtColumn{
		Name: field.Name,
	}

	if field.Description != nil {
		dbtColumn.Description = *field.Description
	}

	if field.Type != nil {
		dbtColumn.DataType = *field.Description
	}

	if field.Required {
		dbtColumn.Constraints = append(dbtColumn.Constraints, dbtConstraint{Type: "not_null"})
	}

	if field.Unique {
		dbtColumn.Constraints = append(dbtColumn.Constraints, dbtConstraint{Type: "unique"})
	}

	for _, constraint := range field.AdditionalConstraints {
		dbtConstraint := dbtConstraint{
			Type:       constraint.Type,
			Expression: constraint.Expression,
		}
		dbtColumn.Constraints = append(dbtColumn.Constraints, dbtConstraint)
	}
	return dbtColumn
}

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

func parseDbtDataset(specification []byte) InternalModelSpecification {
	var res dbtSpecification

	yaml.Unmarshal(specification, &res)
	models := modelsFromDbtSpecification(res)

	return InternalModelSpecification{Type: "dbt", Models: models}
}

func modelsFromDbtSpecification(res dbtSpecification) (models []InternalModel) {
	for _, model := range res.Models {
		modelType := model.Config.Materialized
		modelDescription := model.Description

		models = append(models, InternalModel{
			Name:        model.Name,
			Type:        &modelType,
			Description: &modelDescription,
			Fields:      fieldsFromDbtModel(model),
		})
	}

	return models
}

func fieldsFromDbtModel(model dbtModel) (fields []InternalField) {
	for _, column := range model.Columns {
		allDbtConstraints := combineDbtConstraints(model, column)

		columnType := column.DataType
		columnDescription := column.Description

		fields = append(fields, InternalField{
			Name:                  column.Name,
			Type:                  &columnType,
			Description:           &columnDescription,
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

	result = append(result, column.Constraints...)

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

func additionalDbtConstraints(allDbtConstraints []dbtConstraint) (result []InternalFieldConstraint) {
	for _, constraint := range allDbtConstraints {
		if constraint.Type != "not_null" && constraint.Type != "unique" {
			result = append(result,
				InternalFieldConstraint{Type: constraint.Type, Expression: constraint.Expression})
		}
	}

	return result
}
