package main

import (
	"fmt"
	"gopkg.in/yaml.v3"
	"log"
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
	FieldName   *string
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
	DatasetDifferenceTypeDatasetSchemaTypeChanged
	DatasetDifferenceTypeModelAdded
	DatasetDifferenceTypeModelTypeChanged
	DatasetDifferenceTypeFieldAdded
	DatasetDifferenceTypeFieldRequirementAdded
	DatasetDifferenceTypeFieldUniquenessAdded
	DatasetDifferenceTypeFieldDescriptionChanged
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
	case DatasetDifferenceTypeDatasetSchemaTypeChanged:
		return "dataset-schema-type-changed"
	case DatasetDifferenceTypeModelAdded:
		return "model-added"
	case DatasetDifferenceTypeModelTypeChanged:
		return "model-type-changed"
	case DatasetDifferenceTypeFieldAdded:
		return "field-added"
	case DatasetDifferenceTypeFieldRequirementAdded:
		return "field-requirement-added"
	case DatasetDifferenceTypeFieldUniquenessAdded:
		return "field-uniqueness-added"
	case DatasetDifferenceTypeFieldDescriptionChanged:
		return "field-description-changed"
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
		modelTypeChanged,
		fieldAdded,
		fieldRequirementAdded,
		fieldUniquenessAdded,
		fieldDescriptionChanged,
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
			FieldName:   &fieldName,
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
		if !EqualStringPointers(oldField.Type, newField.Type) {
			return append(result, DatasetDifference{
				Type:      DatasetDifferenceTypeFieldTypeChanged,
				Level:     DatasetDifferenceLevelField,
				Severity:  DatasetDifferenceSeverityBreaking,
				ModelName: &modelName,
				FieldName: &fieldName,
				Description: fmt.Sprintf(
					"type of field '%v.%v' was changed from '%v' to '%v'",
					modelName,
					fieldName,
					StringPointerString(oldField.Type),
					StringPointerString(newField.Type),
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
				FieldName:   &fieldName,
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
				FieldName:   &fieldName,
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
					FieldName: &fieldName,
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
					FieldName: &fieldName,
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
			Type:        DatasetDifferenceTypeDatasetSchemaTypeChanged,
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
				Type:        DatasetDifferenceTypeModelAdded,
				Level:       DatasetDifferenceLevelModel,
				Severity:    DatasetDifferenceSeverityInfo,
				ModelName:   &newModel.Name,
				Description: fmt.Sprintf("model '%v' was added", newModel.Name),
			})
		}
	}

	return result
}

func modelTypeChanged(old, new Dataset) (result []DatasetDifference) {
	for _, oldModel := range old.Models {
		if newModel := oldModel.findEquivalent(new.Models); newModel != nil && !EqualStringPointers(oldModel.Type, newModel.Type) {
			result = append(result, DatasetDifference{
				Type:        DatasetDifferenceTypeModelTypeChanged,
				Level:       DatasetDifferenceLevelModel,
				Severity:    DatasetDifferenceSeverityInfo,
				ModelName:   &oldModel.Name,
				Description: fmt.Sprintf("type of model '%v' was changed from '%v' to '%v'", oldModel.Name, StringPointerString(oldModel.Type), StringPointerString(newModel.Type)),
			})
		}
	}

	return result
}

func fieldAdded(old, new Dataset) (result []DatasetDifference) {
	var difference fieldEquivalentExistsNot = func(
		modelName, fieldName string,
		field Field,
	) (result []DatasetDifference) {
		return append(result, DatasetDifference{
			Type:        DatasetDifferenceTypeFieldAdded,
			Level:       DatasetDifferenceLevelField,
			Severity:    DatasetDifferenceSeverityInfo,
			ModelName:   &modelName,
			FieldName:   &fieldName,
			Description: fmt.Sprintf("field '%v.%v' was added", modelName, fieldName),
		})
	}

	return append(result, compareFields(new, old, nil, &difference)...)
}

func fieldRequirementAdded(old, new Dataset) (result []DatasetDifference) {
	var difference fieldEquivalentExists = func(
		modelName, fieldName string,
		oldField, newField Field,
	) (result []DatasetDifference) {
		if !oldField.Required && newField.Required {
			return append(result, DatasetDifference{
				Type:        DatasetDifferenceTypeFieldRequirementAdded,
				Level:       DatasetDifferenceLevelField,
				Severity:    DatasetDifferenceSeverityInfo,
				ModelName:   &modelName,
				FieldName:   &fieldName,
				Description: fmt.Sprintf("field requirement of '%v.%v' was added", modelName, fieldName),
			})
		} else {
			return result
		}
	}

	return append(result, compareFields(old, new, &difference, nil)...)
}

func fieldUniquenessAdded(old, new Dataset) (result []DatasetDifference) {
	var difference fieldEquivalentExists = func(
		modelName, fieldName string,
		oldField, newField Field,
	) (result []DatasetDifference) {
		if !oldField.Unique && newField.Unique {
			return append(result, DatasetDifference{
				Type:        DatasetDifferenceTypeFieldUniquenessAdded,
				Level:       DatasetDifferenceLevelField,
				Severity:    DatasetDifferenceSeverityInfo,
				ModelName:   &modelName,
				FieldName:   &fieldName,
				Description: fmt.Sprintf("field uniqueness of '%v.%v' was added", modelName, fieldName),
			})
		} else {
			return result
		}
	}

	return append(result, compareFields(old, new, &difference, nil)...)
}

func fieldDescriptionChanged(old, new Dataset) (result []DatasetDifference) {
	var difference fieldEquivalentExists = func(
		modelName, fieldName string,
		oldField, newField Field,
	) (result []DatasetDifference) {
		if !EqualStringPointers(oldField.Description, newField.Description) {
			return append(result, DatasetDifference{
				Type:      DatasetDifferenceTypeFieldDescriptionChanged,
				Level:     DatasetDifferenceLevelField,
				Severity:  DatasetDifferenceSeverityInfo,
				ModelName: &modelName,
				FieldName: &fieldName,
				Description: fmt.Sprintf(
					"description of field '%v.%v' has changed from '%v' to '%v'",
					modelName,
					fieldName,
					StringPointerString(oldField.Description),
					StringPointerString(newField.Description),
				),
			})
		} else {
			return result
		}
	}

	return append(result, compareFields(old, new, &difference, nil)...)
}

func (constraint FieldConstraint) isIn(list []FieldConstraint) bool {
	for _, oldConstraint := range list {
		if constraint.Type == oldConstraint.Type && constraint.Expression == oldConstraint.Expression {
			return true
		}
	}

	return false
}

type fieldEquivalentExists func(
	modelName, prefixedFieldName string,
	left, right Field,
) []DatasetDifference

type fieldEquivalentExistsNot func(
	modelName string,
	prefixedFieldName string,
	field Field,
) []DatasetDifference

// traverse through fields and their subfields
// apply corresponding methods if equivalent field in left dataset exists in right dataset or not
func compareFields(
	left, right Dataset,
	whenEquivalentExists *fieldEquivalentExists,
	whenEquivalentExistsNot *fieldEquivalentExistsNot,
) (result []DatasetDifference) {
	for _, leftModel := range left.Models {
		if rightModel := leftModel.findEquivalent(right.Models); rightModel != nil {
			result = append(
				result,
				compareFieldsRecursive(
					leftModel.Fields,
					rightModel.Fields,
					leftModel.Name,
					nil,
					whenEquivalentExists,
					whenEquivalentExistsNot,
				)...,
			)
		}
	}

	return result
}

func compareFieldsRecursive(
	leftFields, rightFields []Field,
	modelName string,
	fieldPrefix *string,
	whenEquivalentExists *fieldEquivalentExists,
	whenEquivalentExistsNot *fieldEquivalentExistsNot,
) (result []DatasetDifference) {
	for _, leftField := range leftFields {
		fieldName := leftField.prefixedName(fieldPrefix)

		if rightField := leftField.findEquivalent(rightFields); rightField == nil {
			if whenEquivalentExistsNot != nil {
				result = append(result, (*whenEquivalentExistsNot)(modelName, fieldName, leftField)...)
			}
		} else {
			if whenEquivalentExists != nil {
				result = append(result, (*whenEquivalentExists)(modelName, fieldName, leftField, *rightField)...)
			}
			result = append(result,
				compareFieldsRecursive(
					leftField.Fields,
					rightField.Fields,
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

func GetSchemaSpecification(dataContract DataContract, pathToType []string, pathToSpecification []string) (*Dataset, error) {
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

func parseDataset(schemaType string, specification []byte) Dataset {
	switch schemaType {
	case "dbt":
		return parseDbtDataset(specification)
	default:
		return Dataset{}
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

func parseDbtDataset(specification []byte) Dataset {
	var res dbtSpecification

	yaml.Unmarshal(specification, &res)
	models := modelsFromDbtSpecification(res)

	return Dataset{SchemaType: "dbt", Models: models}
}

func modelsFromDbtSpecification(res dbtSpecification) (models []Model) {
	for _, model := range res.Models {
		modelType := model.Config.Materialized
		modelDescription := model.Description

		models = append(models, Model{
			Name:        model.Name,
			Type:        &modelType,
			Description: &modelDescription,
			Fields:      fieldsFromDbtModel(model),
		})
	}

	return models
}

func fieldsFromDbtModel(model dbtModel) (fields []Field) {
	for _, column := range model.Columns {
		allDbtConstraints := combineDbtConstraints(model, column)

		columnType := column.DataType
		columnDescription := column.Description

		fields = append(fields, Field{
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

func additionalDbtConstraints(allDbtConstraints []dbtConstraint) (result []FieldConstraint) {
	for _, constraint := range allDbtConstraints {
		if constraint.Type != "not_null" && constraint.Type != "unique" {
			result = append(result,
				FieldConstraint{Type: constraint.Type, Expression: constraint.Expression})
		}
	}

	return result
}
