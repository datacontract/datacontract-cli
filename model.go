package datacontract

import (
	"fmt"
	"gopkg.in/yaml.v3"
	"io"
	"log"
	"os"
)

// internal model

type InternalModelSpecification struct {
	Type   string
	Models []InternalModel
}

type InternalModel struct {
	Name        string
	Type        *string
	Description *string
	Fields      []InternalField
}

type InternalField struct {
	Name                  string
	Type                  *string
	Description           *string
	Required              bool
	Unique                bool
	AdditionalConstraints []InternalFieldConstraint
	Fields                []InternalField
}

type InternalFieldConstraint struct {
	Type       string
	Expression string
}

// model difference

type ModelDifference struct {
	Type        ModelDifferenceType
	Level       ModelDifferenceLevel
	Severity    ModelDifferenceSeverity
	ModelName   *string
	FieldName   *string
	Description string
}

const InternalModelSpecificationType = "data-contract-specification"

type ModelDifferenceType int

const (
	ModelDifferenceTypeModelRemoved ModelDifferenceType = iota
	ModelDifferenceTypeFieldRemoved
	ModelDifferenceTypeFieldTypeChanged
	ModelDifferenceTypeFieldRequirementRemoved
	ModelDifferenceTypeFieldUniquenessRemoved
	ModelDifferenceTypeFieldAdditionalConstraintAdded
	ModelDifferenceTypeFieldAdditionalConstraintRemoved
	ModelDifferenceTypeDatasetSchemaTypeChanged
	ModelDifferenceTypeModelAdded
	ModelDifferenceTypeModelTypeChanged
	ModelDifferenceTypeFieldAdded
	ModelDifferenceTypeFieldRequirementAdded
	ModelDifferenceTypeFieldUniquenessAdded
	ModelDifferenceTypeFieldDescriptionChanged
)

func (d ModelDifferenceType) String() string {
	switch d {
	// breaking
	case ModelDifferenceTypeModelRemoved:
		return "model-removed"
	case ModelDifferenceTypeFieldRemoved:
		return "field-removed"
	case ModelDifferenceTypeFieldTypeChanged:
		return "field-type-changed"
	case ModelDifferenceTypeFieldRequirementRemoved:
		return "field-requirement-removed"
	case ModelDifferenceTypeFieldUniquenessRemoved:
		return "field-uniqueness-removed"
	case ModelDifferenceTypeFieldAdditionalConstraintRemoved:
		return "field-constraint-removed"
	case ModelDifferenceTypeFieldAdditionalConstraintAdded:
		return "field-constraint-added"
	// info
	case ModelDifferenceTypeDatasetSchemaTypeChanged:
		return "dataset-schema-type-changed"
	case ModelDifferenceTypeModelAdded:
		return "model-added"
	case ModelDifferenceTypeModelTypeChanged:
		return "model-type-changed"
	case ModelDifferenceTypeFieldAdded:
		return "field-added"
	case ModelDifferenceTypeFieldRequirementAdded:
		return "field-requirement-added"
	case ModelDifferenceTypeFieldUniquenessAdded:
		return "field-uniqueness-added"
	case ModelDifferenceTypeFieldDescriptionChanged:
		return "field-description-changed"
	}

	return ""
}

type ModelDifferenceLevel int

const (
	ModelDifferenceLevelDataset ModelDifferenceLevel = iota
	ModelDifferenceLevelModel
	ModelDifferenceLevelField
)

func (d ModelDifferenceLevel) String() string {
	switch d {
	case ModelDifferenceLevelDataset:
		return "dataset"
	case ModelDifferenceLevelModel:
		return "model"
	case ModelDifferenceLevelField:
		return "field"
	}

	return ""
}

type ModelDifferenceSeverity int

const (
	ModelDifferenceSeverityInfo ModelDifferenceSeverity = iota
	ModelDifferenceSeverityBreaking
)

func (d ModelDifferenceSeverity) String() string {
	switch d {
	case ModelDifferenceSeverityInfo:
		return "info"
	case ModelDifferenceSeverityBreaking:
		return "breaking"
	}

	return ""
}

type datasetComparison = func(old, new InternalModelSpecification) []ModelDifference

func CompareModelSpecifications(old, new InternalModelSpecification) (result []ModelDifference) {
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

func modelRemoved(old, new InternalModelSpecification) (result []ModelDifference) {
	for _, oldModel := range old.Models {
		if oldModel.findEquivalent(new.Models) == nil {
			result = append(result, ModelDifference{
				Type:        ModelDifferenceTypeModelRemoved,
				Level:       ModelDifferenceLevelModel,
				Severity:    ModelDifferenceSeverityBreaking,
				ModelName:   &oldModel.Name,
				Description: fmt.Sprintf("model '%v' was removed", oldModel.Name),
			})
		}
	}

	return result
}

func fieldRemoved(old, new InternalModelSpecification) (result []ModelDifference) {
	var difference fieldEquivalentExistsNot = func(
		modelName, fieldName string,
		field InternalField,
	) (result []ModelDifference) {
		return append(result, ModelDifference{
			Type:        ModelDifferenceTypeFieldRemoved,
			Level:       ModelDifferenceLevelField,
			Severity:    ModelDifferenceSeverityBreaking,
			ModelName:   &modelName,
			FieldName:   &fieldName,
			Description: fmt.Sprintf("field '%v.%v' was removed", modelName, fieldName),
		})
	}

	return append(result, compareFields(old, new, nil, &difference)...)
}

func fieldTypeChanged(old, new InternalModelSpecification) (result []ModelDifference) {
	var difference fieldEquivalentExists = func(
		modelName, fieldName string,
		oldField, newField InternalField,
	) (result []ModelDifference) {
		if !EqualStringPointers(oldField.Type, newField.Type) {
			return append(result, ModelDifference{
				Type:      ModelDifferenceTypeFieldTypeChanged,
				Level:     ModelDifferenceLevelField,
				Severity:  ModelDifferenceSeverityBreaking,
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

func fieldRequirementRemoved(old, new InternalModelSpecification) (result []ModelDifference) {
	var difference fieldEquivalentExists = func(
		modelName, fieldName string,
		oldField, newField InternalField,
	) (result []ModelDifference) {
		if oldField.Required && !newField.Required {
			return append(result, ModelDifference{
				Type:        ModelDifferenceTypeFieldRequirementRemoved,
				Level:       ModelDifferenceLevelField,
				Severity:    ModelDifferenceSeverityBreaking,
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

func fieldUniquenessRemoved(old, new InternalModelSpecification) (result []ModelDifference) {
	var difference fieldEquivalentExists = func(
		modelName, fieldName string,
		oldField, newField InternalField,
	) (result []ModelDifference) {
		if oldField.Unique && !newField.Unique {
			return append(result, ModelDifference{
				Type:        ModelDifferenceTypeFieldUniquenessRemoved,
				Level:       ModelDifferenceLevelField,
				Severity:    ModelDifferenceSeverityBreaking,
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

func fieldConstraintAdded(old, new InternalModelSpecification) (result []ModelDifference) {
	var difference fieldEquivalentExists = func(
		modelName, fieldName string,
		oldField, newField InternalField,
	) (result []ModelDifference) {
		for _, constraint := range newField.AdditionalConstraints {
			if !constraint.isIn(oldField.AdditionalConstraints) {
				result = append(result, ModelDifference{
					Type:      ModelDifferenceTypeFieldAdditionalConstraintAdded,
					Level:     ModelDifferenceLevelField,
					Severity:  ModelDifferenceSeverityBreaking,
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

func fieldConstraintRemoved(old, new InternalModelSpecification) (result []ModelDifference) {
	var difference fieldEquivalentExists = func(
		modelName, fieldName string,
		oldField, newField InternalField,
	) (result []ModelDifference) {
		for _, constraint := range oldField.AdditionalConstraints {
			if !constraint.isIn(newField.AdditionalConstraints) {
				result = append(result, ModelDifference{
					Type:      ModelDifferenceTypeFieldAdditionalConstraintRemoved,
					Level:     ModelDifferenceLevelField,
					Severity:  ModelDifferenceSeverityBreaking,
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

func datasetSchemaTypeChanged(old, new InternalModelSpecification) (result []ModelDifference) {
	if old.Type != new.Type {
		result = append(result, ModelDifference{
			Type:        ModelDifferenceTypeDatasetSchemaTypeChanged,
			Level:       ModelDifferenceLevelDataset,
			Severity:    ModelDifferenceSeverityInfo,
			Description: fmt.Sprintf("schema type changed from '%v' to '%v'", old.Type, new.Type),
		})
	}
	return result
}

func modelAdded(old, new InternalModelSpecification) (result []ModelDifference) {
	for _, newModel := range new.Models {
		if newModel.findEquivalent(old.Models) == nil {
			result = append(result, ModelDifference{
				Type:        ModelDifferenceTypeModelAdded,
				Level:       ModelDifferenceLevelModel,
				Severity:    ModelDifferenceSeverityInfo,
				ModelName:   &newModel.Name,
				Description: fmt.Sprintf("model '%v' was added", newModel.Name),
			})
		}
	}

	return result
}

func modelTypeChanged(old, new InternalModelSpecification) (result []ModelDifference) {
	for _, oldModel := range old.Models {
		if newModel := oldModel.findEquivalent(new.Models); newModel != nil && !EqualStringPointers(oldModel.Type, newModel.Type) {
			result = append(result, ModelDifference{
				Type:        ModelDifferenceTypeModelTypeChanged,
				Level:       ModelDifferenceLevelModel,
				Severity:    ModelDifferenceSeverityInfo,
				ModelName:   &oldModel.Name,
				Description: fmt.Sprintf("type of model '%v' was changed from '%v' to '%v'", oldModel.Name, StringPointerString(oldModel.Type), StringPointerString(newModel.Type)),
			})
		}
	}

	return result
}

func fieldAdded(old, new InternalModelSpecification) (result []ModelDifference) {
	var difference fieldEquivalentExistsNot = func(
		modelName, fieldName string,
		field InternalField,
	) (result []ModelDifference) {
		return append(result, ModelDifference{
			Type:        ModelDifferenceTypeFieldAdded,
			Level:       ModelDifferenceLevelField,
			Severity:    ModelDifferenceSeverityInfo,
			ModelName:   &modelName,
			FieldName:   &fieldName,
			Description: fmt.Sprintf("field '%v.%v' was added", modelName, fieldName),
		})
	}

	return append(result, compareFields(new, old, nil, &difference)...)
}

func fieldRequirementAdded(old, new InternalModelSpecification) (result []ModelDifference) {
	var difference fieldEquivalentExists = func(
		modelName, fieldName string,
		oldField, newField InternalField,
	) (result []ModelDifference) {
		if !oldField.Required && newField.Required {
			return append(result, ModelDifference{
				Type:        ModelDifferenceTypeFieldRequirementAdded,
				Level:       ModelDifferenceLevelField,
				Severity:    ModelDifferenceSeverityInfo,
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

func fieldUniquenessAdded(old, new InternalModelSpecification) (result []ModelDifference) {
	var difference fieldEquivalentExists = func(
		modelName, fieldName string,
		oldField, newField InternalField,
	) (result []ModelDifference) {
		if !oldField.Unique && newField.Unique {
			return append(result, ModelDifference{
				Type:        ModelDifferenceTypeFieldUniquenessAdded,
				Level:       ModelDifferenceLevelField,
				Severity:    ModelDifferenceSeverityInfo,
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

func fieldDescriptionChanged(old, new InternalModelSpecification) (result []ModelDifference) {
	var difference fieldEquivalentExists = func(
		modelName, fieldName string,
		oldField, newField InternalField,
	) (result []ModelDifference) {
		if !EqualStringPointers(oldField.Description, newField.Description) {
			return append(result, ModelDifference{
				Type:      ModelDifferenceTypeFieldDescriptionChanged,
				Level:     ModelDifferenceLevelField,
				Severity:  ModelDifferenceSeverityInfo,
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

func (constraint InternalFieldConstraint) isIn(list []InternalFieldConstraint) bool {
	for _, oldConstraint := range list {
		if constraint.Type == oldConstraint.Type && constraint.Expression == oldConstraint.Expression {
			return true
		}
	}

	return false
}

type fieldEquivalentExists func(
	modelName, prefixedFieldName string,
	left, right InternalField,
) []ModelDifference

type fieldEquivalentExistsNot func(
	modelName string,
	prefixedFieldName string,
	field InternalField,
) []ModelDifference

// traverse through fields and their subfields
// apply corresponding methods if equivalent field in left dataset exists in right dataset or not
func compareFields(
	left, right InternalModelSpecification,
	whenEquivalentExists *fieldEquivalentExists,
	whenEquivalentExistsNot *fieldEquivalentExistsNot,
) (result []ModelDifference) {
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
	leftFields, rightFields []InternalField,
	modelName string,
	fieldPrefix *string,
	whenEquivalentExists *fieldEquivalentExists,
	whenEquivalentExistsNot *fieldEquivalentExistsNot,
) (result []ModelDifference) {
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

func (field InternalField) prefixedName(prefix *string) string {
	var fieldName string
	if prefix == nil {
		fieldName = field.Name
	} else {
		fieldName = fmt.Sprintf("%v.%v", *prefix, field.Name)
	}
	return fieldName
}

func (model InternalModel) findEquivalent(otherModels []InternalModel) (result *InternalModel) {
	for _, newModel := range otherModels {
		if model.Name == newModel.Name {
			result = &newModel
			break
		}
	}
	return result
}

func (field InternalField) findEquivalent(otherFields []InternalField) (result *InternalField) {
	for _, newField := range otherFields {
		if field.Name == newField.Name {
			result = &newField
			break
		}
	}
	return result
}

func GetModelsFromSpecification(contract DataContract, pathToModels []string) (*InternalModelSpecification, error) {
	sm, err := GetValue(contract, pathToModels)
	if err != nil {
		// ignore if no contract was found
		return nil, nil
	}

	specModels, err := enforceMap(sm)
	if err != nil {
		return nil, err
	}

	// inline all references inside the models section
	InlineReferences(&specModels, contract)

	if err != nil {
		// only warn on error to be compatible to embedded schema notation, this should fail, when schema support is dropped
		log.Printf("Can not resolve specModels for path %v: %v", pathToModels, err)
		return nil, nil
	}

	modelsMap, err := enforceMap(specModels)
	if err != nil {
		return nil, err
	}

	return internalModelSpecification(modelsMap)
}

func internalModelSpecification(modelsMap map[string]any) (*InternalModelSpecification, error) {
	var internalModels []InternalModel

	for modelName, specModel := range modelsMap {
		specModelMap, err := enforceMap(specModel)
		if err != nil {
			return nil, err
		}

		model, err := internalModel(specModelMap, modelName)
		if err != nil {
			return nil, err
		}

		internalModels = append(internalModels, *model)
	}

	return &InternalModelSpecification{Type: InternalModelSpecificationType, Models: internalModels}, nil
}

func internalModel(specModel map[string]any, modelName string) (*InternalModel, error) {
	modelType, err := fieldAsString(specModel, "type")
	if err != nil {
		return nil, err
	}

	modelDescription, err := fieldAsString(specModel, "description")
	if err != nil {
		return nil, err
	}

	internalFields, err := internalFields(specModel)
	if err != nil {
		return nil, err
	}

	return &InternalModel{
		Name:        modelName,
		Type:        modelType,
		Description: modelDescription,
		Fields:      internalFields,
	}, nil
}

func internalFields(specModelMap map[string]any) ([]InternalField, error) {
	var internalFields []InternalField

	fields := specModelMap["fields"]
	if fields != nil {
		fieldsMap, err := enforceMap(fields)
		if err != nil {
			return nil, err
		}

		for fieldName, specField := range fieldsMap {
			fieldMap, err := enforceMap(specField)
			if err != nil {
				return nil, err
			}

			internalField, err := internalField(fieldMap, fieldName)
			if err != nil {
				return nil, err
			}

			internalFields = append(internalFields, *internalField)
		}
	}

	return internalFields, nil
}

func internalField(fieldMap map[string]any, fieldName string) (*InternalField, error) {
	fieldType, err := fieldAsString(fieldMap, "type")
	if err != nil {
		return nil, err
	}

	fieldDescription, err := fieldAsString(fieldMap, "description")
	if err != nil {
		return nil, err
	}

	return &InternalField{
		Name:        fieldName,
		Type:        fieldType,
		Description: fieldDescription,
	}, nil
}

func enforceMap(field any) (map[string]any, error) {
	if anyMap, isMap := field.(map[string]any); !isMap {
		return nil, fmt.Errorf("field is not a map")
	} else {
		return anyMap, nil
	}
}

func fieldAsString(anyMap map[string]any, fieldName string) (*string, error) {
	field := anyMap[fieldName]

	if field == nil {
		return nil, nil
	}

	if result, ok := field.(string); !ok {
		return nil, fmt.Errorf("field %v is not a map", fieldName)
	} else {
		return &result, nil
	}
}

func InsertModel(dataContractLocation string, model []byte, modelFormat string, pathToModels []string) error {
	contract, err := GetDataContract(dataContractLocation)
	if err != nil {
		return err
	}

	var models map[string]any

	if modelFormat == InternalModelSpecificationType {
		models, err = parseModels(model)
		if err != nil {
			return err
		}
	} else {
		models = ParseSchema(modelFormat, model).asMapForDataContract()
	}

	SetValue(contract, pathToModels, models)

	result, err := ToYaml(contract)
	if err != nil {
		return err
	}

	err = os.WriteFile(dataContractLocation, result, os.ModePerm)
	if err != nil {
		return err
	}

	return nil
}

func parseModels(model []byte) (map[string]any, error) {
	modelsFromInput := map[string]any{}
	yaml.Unmarshal(model, modelsFromInput)

	// convert to spec model and back to map, to clean / validate the input
	specification, err := internalModelSpecification(modelsFromInput)
	if err != nil {
		return nil, err
	}
	return specification.asMapForDataContract(), nil
}

func (specification InternalModelSpecification) asMapForDataContract() map[string]any {
	models := map[string]any{}

	for _, model := range specification.Models {
		models[model.Name] = model.asMapForDataContract()
	}

	return models
}

func (model InternalModel) asMapForDataContract() map[string]any {
	modelAsMAp := map[string]any{}

	if model.Type != nil {
		modelAsMAp["type"] = *model.Type
	} else {
		modelAsMAp["type"] = "table"
	}

	if model.Description != nil {
		modelAsMAp["description"] = *model.Description
	}

	fields := map[string]any{}
	for _, field := range model.Fields {
		fields[field.Name] = field.asMapForDataContract()
	}

	modelAsMAp["fields"] = fields

	return modelAsMAp
}

func (field InternalField) asMapForDataContract() map[string]any {
	fieldAsMap := map[string]any{}

	if field.Type != nil {
		fieldAsMap["type"] = *field.Type
	}
	if field.Description != nil {
		fieldAsMap["description"] = *field.Description
	}

	return fieldAsMap
}

func PrintModel(dataContractLocation string, modelType string, pathToModels []string, target io.Writer) error {
	contract, err := GetDataContract(dataContractLocation)
	if err != nil {
		return err
	}

	var output []byte

	if modelType == InternalModelSpecificationType {
		models, err := GetValue(contract, pathToModels)
		if err != nil {
			return err
		}

		output, err = yaml.Marshal(models.(map[string]any))
		if err != nil {
			return err
		}
	} else {
		specification, err := GetModelsFromSpecification(contract, pathToModels)
		if err != nil {
			return err
		}

		output, err = CreateSchema(modelType, *specification)
		if err != nil {
			return err
		}
	}

	Log(target, string(output))

	return nil
}
