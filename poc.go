package main

import (
	"fmt"
	"gopkg.in/yaml.v3"
	"os"
)

func main() {
	fmt.Println("\nAhoy!")

	var err error

	file, err := os.ReadFile("schema.json")
	schema, err := GenerateSchema(file)

	if err != nil {
		fmt.Println("Error reading json schema: ", err)
		return
	}

	promptResults := make(map[string]string)
	for _, field := range schema.collectRequiredFields() {
		promptResults[field.Identifier] = field.prompt()
	}

	yamlBytes, _ := yaml.Marshal(schema.yamlMap(promptResults))
	fmt.Println("---")
	fmt.Println(string(yamlBytes))
}

func (schema Schema) yamlMap(promptResults map[string]string) map[string]any {
	yamlMap := make(map[string]any)

	for _, schemaField := range schema {
		if schemaField.Type == SchemaFieldTypeObject {
			yamlMap[schemaField.FieldName] = schemaField.ObjectSchema.yamlMap(promptResults)
		} else if value, ok := promptResults[schemaField.Identifier]; ok {
			yamlMap[schemaField.FieldName] = value
		} else if schemaField.Type == SchemaFieldTypeArray {
			yamlMap[schemaField.FieldName] = []any{}
		} else if schemaField.Type == SchemaFieldTypeString {
			yamlMap[schemaField.FieldName] = ""
		} else {
			yamlMap[schemaField.FieldName] = nil
		}
	}

	return yamlMap
}

type RequiredField struct {
	Identifier  string
	Description *string
}

func (field RequiredField) prompt() string {
	// todo: special fields
	//if fieldIdentifier == "info.id"
	//if fieldIdentifier == "dataContractSpecification"
	// todo: actual user input, validation...
	//if field.Description != nil {
	//	fmt.Printf("Please enter %v: %v\n", field.Identifier, *field.Description)
	//} else {
	//	fmt.Printf("Please enter %v\n", field.Identifier)
	//}
	return "todo"
}

func (schema Schema) collectRequiredFields() []RequiredField {
	var result []RequiredField

	for _, schemaField := range schema {
		if schemaField.Required {
			if schemaField.Type != SchemaFieldTypeObject {
				result = append(result, RequiredField{schemaField.Identifier, schemaField.Description})
			} else {
				result = append(result, (*schemaField.ObjectSchema).collectRequiredFields()...)
			}
		}
	}

	return result
}
