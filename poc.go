package main

import (
	"bufio"
	"fmt"
	"github.com/google/uuid"
	"gopkg.in/yaml.v3"
	"os"
	"strings"
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
	// todo write file
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
	var suggestion string

	switch field.Identifier {
	case "dataContractSpecification":
		return "0.0.1" // fix version for now
	case "info.id":
		suggestion = uuid.NewString()
	}

	if field.Description != nil {
		fmt.Printf("Please enter %v: %v\n", field.Identifier, *field.Description)
	} else {
		fmt.Printf("Please enter %v\n", field.Identifier)
	}

	if suggestion != "" {
		fmt.Printf("type value or press enter to use %v\n", suggestion)
	}

	reader := bufio.NewReader(os.Stdin)

	input, _ := reader.ReadString('\n')
	input = strings.TrimSuffix(input, "\n")

	if suggestion != "" && input == "" {
		return suggestion
	}

	// todo: input validation

	return input
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
