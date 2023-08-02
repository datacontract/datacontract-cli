package main

import (
	"encoding/json"
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
	Default      string
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

func (schema *Schema) Sort() {
	sort.Sort(schema)

	for _, schemaField := range *schema {
		if schemaField.Type == SchemaFieldTypeObject {
			schemaField.ObjectSchema.Sort()
		}
	}

	schema.swapWellKnownFields()
}

func (schema *Schema) swapWellKnownFields() {
	for i, schemaField := range *schema {
		switch schemaField.Identifier {
		case "dataContractSpecification":
			schema.Swap(0, i)
		case "info":
			schema.Swap(1, i)
		case "info.id":
			schema.Swap(0, i)
		}
	}
}

func (schema *Schema) Len() int {
	return len(*schema)
}

func (schema *Schema) Less(i, j int) bool {
	return (*schema)[i].FieldName < (*schema)[j].FieldName
}

func (schema *Schema) Swap(i, j int) {
	(*schema)[i], (*schema)[j] = (*schema)[j], (*schema)[i]
}

func GenerateSchema(jsonSchema []byte) (*Schema, error) {
	var schemaMap map[string]any

	err := json.Unmarshal(jsonSchema, &schemaMap)

	if err != nil {
		return nil, err
	}

	return generateSchema(schemaMap, ""), nil
}

func generateSchema(jsonSchema map[string]any, identifierPrefix string) *Schema {
	schema := Schema{}
	requiredFields, requiredFieldExists := jsonSchema["required"].([]any)
	properties, propertiesFieldExists := jsonSchema["properties"].(map[string]any)

	if !propertiesFieldExists {
		return &schema
	}

	if !requiredFieldExists {
		requiredFields = make([]any, 0)
	}

	for key, value := range properties {
		field := value.(map[string]any)
		identifier := identifierPrefix + "." + key

		schemaField := SchemaField{
			Type:        schemaFieldType(field),
			FieldName:   key,
			Identifier:  identifier[1:],
			Description: description(field),
			Required:    contains(requiredFields, key),
		}

		if defaultValue, ok := field["default"].(string); ok {
			schemaField.Default = defaultValue
		}

		if schemaField.Type == SchemaFieldTypeObject {
			schemaField.ObjectSchema = generateSchema(field, identifier)
		}

		schema = append(schema, schemaField)
	}

	return &schema
}

func schemaFieldType(field map[string]any) SchemaFieldType {
	fieldType, hasType := field["type"].(string)
	format, hasFormat := field["format"].(string)

	if !hasType {
		return SchemaFiledTypeUnknown
	} else if fieldType == "string" && hasFormat {
		return SchemaFieldType(format)
	} else {
		return SchemaFieldType(fieldType)
	}
}

func description(field map[string]any) *string {
	if description, ok := field["description"].(string); ok {
		return &description
	} else {
		return nil
	}
}

func contains(slice []any, value any) bool {
	for _, item := range slice {
		if item == value {
			return true
		}
	}
	return false
}
