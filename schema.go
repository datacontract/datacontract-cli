package main

import (
	"encoding/json"
	"fmt"
	"math"
	"os"
	"sort"
)

type Schema []SchemaField

type SchemaField struct {
	Type         SchemaFieldType
	FieldName    string
	Identifier   string
	Description  *string
	Required     bool
	ObjectSchema *Schema
	Default      *string
}

type SchemaFieldType string

const (
	SchemaFieldTypeObject   SchemaFieldType = "object"
	SchemaFieldTypeArray    SchemaFieldType = "array"
	SchemaFieldTypeString   SchemaFieldType = "string"
	SchemaFieldTypeDate     SchemaFieldType = "date"
	SchemaFieldTypeDuration SchemaFieldType = "duration"
	SchemaFiledTypeUnknown  SchemaFieldType = "unknown"
)

var sortingPriority = map[string]uint8{
	"dataContractSpecification": math.MaxUint8,
	"info":                      math.MaxUint8 - 1,
	"info.id":                   math.MaxUint8,
	"info.purpose":              math.MaxUint8 - 1,
}

func (schema *Schema) Sort() {
	sort.Sort(schema)

	for _, schemaField := range *schema {
		if schemaField.ObjectSchema != nil {
			schemaField.ObjectSchema.Sort()
		}
	}
}

func (schema *Schema) Len() int {
	return len(*schema)
}

func (schema *Schema) Less(i, j int) bool {
	fieldLeft := (*schema)[i]
	fieldRight := (*schema)[j]

	priorityLeft := sortingPriority[fieldLeft.Identifier]
	priorityRight := sortingPriority[fieldRight.Identifier]

	if priorityLeft+priorityRight != 0 {
		return priorityLeft > priorityRight
	} else {
		return fieldLeft.FieldName < fieldRight.FieldName
	}
}

func (schema *Schema) Swap(i, j int) {
	(*schema)[i], (*schema)[j] = (*schema)[j], (*schema)[i]
}

func (schema *Schema) Flattened() []SchemaField {
	var result []SchemaField

	for _, field := range *schema {
		if field.Type != SchemaFieldTypeObject {
			result = append(result, field)
		} else if field.ObjectSchema != nil {
			result = append(result, field.ObjectSchema.Flattened()...)
		}
	}

	return result
}

func ReadSchema(version string) (schema *Schema, err error) {
	schemaFileName := fmt.Sprintf("schema-%v.json", version)
	jsonSchema, err := os.ReadFile(schemaFileName)
	schema, err = generateSchema(jsonSchema)

	if schema != nil {
		schema.Sort()
	}

	return schema, err
}

func generateSchema(jsonSchema []byte) (schema *Schema, err error) {
	schemaMap := make(map[string]any)
	err = json.Unmarshal(jsonSchema, &schemaMap)
	schema = generateSchemaRecursive(schemaMap, "")

	return schema, err
}

func generateSchemaRecursive(jsonSchema map[string]any, identifierPrefix string) *Schema {
	schema := Schema{}
	requiredFields := requiredFields(jsonSchema)

	if properties, exists := jsonSchema["properties"].(map[string]any); exists {

		for key, value := range properties {
			jsonSchemaProperty := value.(map[string]any)
			identifier := identifierPrefix + "." + key
			isRequired := contains(requiredFields, key)
			schemaField := generateSchemaField(jsonSchemaProperty, key, identifier, isRequired)

			if schemaField.Type == SchemaFieldTypeObject {
				schemaField.ObjectSchema = generateSchemaRecursive(jsonSchemaProperty, identifier)
			}

			schema = append(schema, schemaField)
		}

	}

	return &schema
}

func requiredFields(jsonSchema map[string]any) []any {
	fields, requiredFieldExists := jsonSchema["required"].([]any)
	if !requiredFieldExists {
		fields = make([]any, 0)
	}
	return fields
}

func contains(slice []any, value string) bool {
	for _, item := range slice {
		if item == value {
			return true
		}
	}

	return false
}

func generateSchemaField(
	jsonSchemaProperty map[string]any,
	key string,
	identifier string,
	isRequired bool,
) SchemaField {
	return SchemaField{
		Type:        schemaFieldType(jsonSchemaProperty),
		FieldName:   key,
		Identifier:  identifier[1:],
		Description: description(jsonSchemaProperty),
		Required:    isRequired,
		Default:     defaultValue(jsonSchemaProperty),
	}
}

func defaultValue(jsonSchemaProperty map[string]any) *string {
	if value, ok := jsonSchemaProperty["default"].(string); ok {
		return &value
	} else {
		return nil
	}
}

func schemaFieldType(jsonSchemaProperty map[string]any) SchemaFieldType {
	fieldType, hasType := jsonSchemaProperty["type"].(string)
	format, hasFormat := jsonSchemaProperty["format"].(string)

	if !hasType {
		return SchemaFiledTypeUnknown
	} else if fieldType == "string" && hasFormat {
		return SchemaFieldType(format)
	} else {
		return SchemaFieldType(fieldType)
	}
}

func description(jsonSchemaProperty map[string]any) *string {
	if description, ok := jsonSchemaProperty["description"].(string); ok {
		return &description
	} else {
		return nil
	}
}
