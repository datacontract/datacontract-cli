package main

import (
	"encoding/json"
)

type Schema []SchemaField

type SchemaField struct {
	Type         string // todo enum
	FieldName    string
	Identifier   string
	Description  *string
	Required     bool
	ObjectSchema *Schema
}

func GenerateSchema(jsonSchema []byte) (*Schema, error) {
	var schemaMap map[string]any

	err := json.Unmarshal(jsonSchema, &schemaMap)

	if err != nil {
		return nil, err
	}

	return generateSchema(schemaMap, ""), nil
}

// todo error handling
func generateSchema(jsonSchema map[string]any, identifierPrefix string) *Schema {
	schema := Schema{}
	requiredFields, _ := jsonSchema["required"].([]any)
	properties := jsonSchema["properties"].(map[string]any)

	for key, value := range properties {
		field := value.(map[string]any)
		fieldType := field["type"].(string)
		identifier := identifierPrefix + "." + key

		schemaField := SchemaField{
			Type:        fieldType,
			FieldName:   key,
			Identifier:  identifier[1:],
			Description: description(field),
			Required:    contains(requiredFields, key),
		}

		if fieldType == "object" {
			schemaField.ObjectSchema = generateSchema(field, identifier)
		}

		schema = append(schema, schemaField)
	}
	// todo: order!

	return &schema
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
