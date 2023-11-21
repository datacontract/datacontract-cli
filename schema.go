package datacontract

import (
	"fmt"
	"gopkg.in/yaml.v3"
	"log"
)

func PrintSchema(dataContractLocation string, pathToSpecification []string) error {
	dataContract, err := GetDataContract(dataContractLocation)
	if err != nil {
		return fmt.Errorf("failed reading data contract: %w", err)
	}

	specification, err := getSpecification(dataContract, pathToSpecification)
	if err != nil {
		return fmt.Errorf("can't get specification: %w", err)
	}

	log.Println(string(TakeStringOrMarshall(specification)))

	return nil
}

func GetModelSpecificationFromSchema(dataContract DataContract, pathToType []string, pathToSpecification []string) (*InternalModelSpecification, error) {
	schemaType, schemaSpecification, err := extractSchemaSpecification(dataContract, pathToType, pathToSpecification)
	if err != nil {
		return nil, fmt.Errorf("failed extracting schema specification: %w", err)
	}

	schemaSpecificationBytes := TakeStringOrMarshall(schemaSpecification)
	parsedDataset := parseDataset(schemaType, schemaSpecificationBytes)

	return &parsedDataset, err
}

func extractSchemaSpecification(
	contract DataContract,
	pathToType []string,
	pathToSpecification []string,
) (schemaType string, specification interface{}, err error) {
	schemaType, err = getSchemaType(contract, pathToType)
	if err != nil {
		log.Println(fmt.Errorf("can't get schema type: %w", err))
	}

	specification, err = getSpecification(contract, pathToSpecification)
	if err != nil {
		log.Println(fmt.Errorf("can't get specification: %w", err))
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

func getSpecification(contract DataContract, path []string) (specification interface{}, err error) {
	specification, err = GetValue(contract, path)
	if err != nil {
		return nil, fmt.Errorf("can't get value of schema specification for path %v: %w", path, err)
	}

	return specification, nil
}

func parseDataset(schemaType string, specification []byte) InternalModelSpecification {
	switch schemaType {
	case "dbt":
		return parseDbtDataset(specification)
	default:
		return InternalModelSpecification{}
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

func additionalDbtConstraints(allDbtConstraints []dbtConstraint) (result []InternalFieldConstraint) {
	for _, constraint := range allDbtConstraints {
		if constraint.Type != "not_null" && constraint.Type != "unique" {
			result = append(result,
				InternalFieldConstraint{Type: constraint.Type, Expression: constraint.Expression})
		}
	}

	return result
}
