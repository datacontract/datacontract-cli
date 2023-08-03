package main

import (
	"bufio"
	"fmt"
	"github.com/google/uuid"
	"gopkg.in/yaml.v3"
	"os"
	"strings"
	"time"
)

type suggestion struct {
	Value       string
	Description string
}

func Init(version, path string) (err error) {
	schema, err := ReadSchema(version)
	if err != nil {
		return err
	}

	values := make(map[string]string)

	fillFieldsBeforePrompts(version, values)

	err = promptRequiredFields(*schema, values)
	if err != nil {
		return err
	}

	fillFieldsAfterPrompts(*schema, values)

	return createDataContractSpecificationFile(inSchema(values, *schema), path)
}

func fillFieldsBeforePrompts(version string, values map[string]string) {
	values["dataContractSpecification"] = version
}

func fillFieldsAfterPrompts(schema Schema, values map[string]string) {
	for _, field := range schema.Flattened() {
		if field.Default != nil && values[field.Identifier] == "" {
			values[field.Identifier] = *field.Default
		}
	}
}

func promptRequiredFields(schema Schema, values map[string]string) (err error) {
	for _, field := range schema.Flattened() {
		if field.Required && values[field.Identifier] == "" {
			values[field.Identifier], err = prompt(fieldMessage(field), fieldSuggestion(field))
		}

		if err != nil {
			return err
		}
	}

	return nil
}

func fieldMessage(field SchemaField) string {
	if field.Description != nil {
		return fmt.Sprintf("Please type value for %v: %v\n", field.Identifier, *field.Description)
	} else {
		return fmt.Sprintf("Please enter %v\n", field.Identifier)
	}
}

func fieldSuggestion(field SchemaField) *suggestion {
	s := fieldSuggestionByIdentifier(field)
	if s != nil {
		return s
	}

	s = fieldSuggestionByDefault(field)
	if s != nil {
		return s
	}

	s = fieldSuggestionByFieldType(field)
	if s != nil {
		return s
	}

	return nil
}

func fieldSuggestionByIdentifier(field SchemaField) *suggestion {
	switch field.Identifier {
	case "info.id":
		return &suggestion{uuid.NewString(), "generated"}
	}
	return nil
}

func fieldSuggestionByFieldType(field SchemaField) *suggestion {
	switch field.Type {
	case SchemaFieldTypeDate:
		return &suggestion{time.Now().Format(time.DateOnly), "today"}
	}
	return nil
}

func fieldSuggestionByDefault(field SchemaField) *suggestion {
	if field.Default != nil {
		return &suggestion{*field.Default, "default"}
	}
	return nil
}

func prompt(message string, suggestion *suggestion) (input string, err error) {
	printMessages(message, suggestion)
	input, err = readUserInput()

	if suggestion != nil && input == "" {
		return suggestion.Value, err
	} else {
		return input, err
	}
}

func printMessages(message string, suggestion *suggestion) {
	fmt.Print(message)
	if suggestion != nil {
		fmt.Printf("💡 press enter to use \"%v\" (%v)\n", suggestion.Value, suggestion.Description)
	}
}

func readUserInput() (input string, err error) {
	reader := bufio.NewReader(os.Stdin)
	input, err = reader.ReadString('\n')

	return strings.TrimSuffix(input, "\n"), err
}

func inSchema(values map[string]string, schema Schema) map[string]any {
	yamlMap := make(map[string]any)

	for _, schemaField := range schema {
		if value, ok := values[schemaField.Identifier]; ok {
			yamlMap[schemaField.FieldName] = value
			continue
		}

		switch schemaField.Type {
		case SchemaFieldTypeObject:
			yamlMap[schemaField.FieldName] = inSchema(values, *schemaField.ObjectSchema)
		case SchemaFieldTypeArray:
			yamlMap[schemaField.FieldName] = []any{}
		case SchemaFieldTypeString, SchemaFieldTypeDate, SchemaFieldTypeDuration:
			yamlMap[schemaField.FieldName] = ""
		default:
			yamlMap[schemaField.FieldName] = nil
		}
	}

	return yamlMap
}

func createDataContractSpecificationFile(values map[string]any, path string) (err error) {
	if path == "" {
		path = "datacontract.yml"
	}

	file, err := os.Create(path)
	defer func() {
		if e := file.Close(); e != nil {
			err = e
		}
	}()

	yamlBytes, err := yaml.Marshal(values)
	result := string(yamlBytes)

	_, err = fmt.Fprint(file, result)

	fmt.Println("---")
	fmt.Println(result)

	return err
}
