package main

import (
	"bufio"
	"encoding/json"
	"errors"
	"fmt"
	"github.com/google/uuid"
	"gopkg.in/yaml.v3"
	"io"
	"net/http"
	"os"
	"strings"
	"time"
)

type suggestion struct {
	Value       string
	Description string
}

type OutputPortSchemaConfiguration struct {
	url     string
	id      string
	headers *[][]string
}

// todo naming?
type dataSourceSchema struct {
	schemaType    string
	specification []byte
}

func Init(version, path string, outputPortSchemaConfiguration *OutputPortSchemaConfiguration) (err error) {

	var dataSourceSchema *dataSourceSchema

	if outputPortSchemaConfiguration != nil {
		dataSourceSchema, err = createDataSourceSchema(version, *outputPortSchemaConfiguration)

		if err != nil {
			return err
		}
	}

	schema, err := ReadSchema(version)
	if err != nil {
		return err
	}

	values := make(map[string]any)

	fillFieldsBeforePrompts(values, version, dataSourceSchema)

	err = promptRequiredFields(values, *schema)
	if err != nil {
		return err
	}

	fillFieldsAfterPrompts(values, *schema)

	return createDataContractSpecificationFile(inSchema(values, *schema), path)
}

func fillFieldsBeforePrompts(values map[string]any, version string, dataSourceSchema *dataSourceSchema) {
	values["dataContractSpecification"] = version

	if dataSourceSchema != nil {
		fillDataSourceSchema(values, *dataSourceSchema)
	}
}

func fillDataSourceSchema(values map[string]any, dataSourceSchema dataSourceSchema) {
	values["schema.type"] = dataSourceSchema.schemaType
	if dataSourceSchema.schemaType == "inline" {
		fillDataSourceInlineSchema(values, dataSourceSchema)
	} else {
		values["schema.specification"] = string(dataSourceSchema.specification)
	}
}

func fillDataSourceInlineSchema(values map[string]any, dataSourceSchema dataSourceSchema) {
	inlineSpecification := make([]any, 0)

	if err := json.Unmarshal(dataSourceSchema.specification, &inlineSpecification); err != nil {
		fmt.Println("Warning: Invalid inline schema specification, inserting as string")
		values["schema.specification"] = string(dataSourceSchema.specification)
	} else {
		values["schema.specification"] = inlineSpecification
	}
}

func fillFieldsAfterPrompts(values map[string]any, schema Schema) {
	for _, field := range schema.Flattened() {
		if field.Default != nil && values[field.Identifier] == "" {
			values[field.Identifier] = *field.Default
		}
	}
}

func promptRequiredFields(values map[string]any, schema Schema) (err error) {
	for _, field := range schema.Flattened() {
		if field.Required && values[field.Identifier] == nil {
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
		return fmt.Sprintf("Please type value for %v: %v", field.Identifier, *field.Description)
	} else {
		return fmt.Sprintf("Please enter %v", field.Identifier)
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

	input = strings.Trim(input, " ")

	if suggestion != nil && input == "" {
		return suggestion.Value, err
	} else {
		return input, err
	}
}

func printMessages(message string, suggestion *suggestion) {
	fmt.Println(message)
	if suggestion != nil {
		fmt.Printf("💡 press enter to use \"%v\" (%v)\n", suggestion.Value, suggestion.Description)
	}
}

func readUserInput() (input string, err error) {
	reader := bufio.NewReader(os.Stdin)
	input, err = reader.ReadString('\n')

	return strings.TrimSuffix(input, "\n"), err
}

func inSchema(values map[string]any, schema Schema) map[string]any {
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

func createDataSourceSchema(version string, config OutputPortSchemaConfiguration) (schema *dataSourceSchema, err error) {
	httpRequest, err := http.NewRequest("GET", config.url, nil)

	if config.headers != nil {
		for _, header := range *config.headers {
			httpRequest.Header.Add(header[0], header[1])
		}
	}

	httpResponse, err := http.DefaultClient.Do(httpRequest)
	defer httpResponse.Body.Close()

	body, err := io.ReadAll(httpResponse.Body)
	bodyMap := make(map[string]any)
	err = json.Unmarshal(body, &bodyMap)

	if httpResponse.StatusCode < 200 || httpResponse.StatusCode >= 300 {
		message := fmt.Sprintf("Failed getting data product from %v: %v", config.url, httpResponse.Status)
		return nil, errors.New(message)
	}

	// depending on the requested version, the following implementation might be dispatched in the future

	if version != bodyMap["dataProductSpecification"] {
		fmt.Println("Warning: dataProductSpecification does not match!")
	}

	var outputPortSchema map[string]any
	for _, op := range bodyMap["outputPorts"].([]any) {
		if op.(map[string]any)["id"] == config.id {
			outputPortSchema = op.(map[string]any)["schema"].(map[string]any)
		}
	}

	outputPortSchemaSpec := outputPortSchema["specification"]
	outputPortSchemaType := outputPortSchema["type"].(string)

	// todo: test this, implement differently for yaml based schema, fall back to string
	if jsonString, ok := outputPortSchemaSpec.(string); ok {
		outputPortSchemaSpec = make(map[string]any, 0)
		outputPortSchemaSpec, err = json.Marshal(jsonString)
	}

	outputPortSchemaSpecBytes, err := json.Marshal(outputPortSchemaSpec)
	fmt.Printf("Found %v schema: %v\n", outputPortSchemaType, string(outputPortSchemaSpecBytes))

	contractSchemaSpec := make([]any, 0)

	switch outputPortSchemaType {
	case "avro":
		if outputPortSchemaList, ok := outputPortSchemaSpec.([]any); ok {
			for _, avroSchema := range outputPortSchemaList {
				if outputPortSchemaEntry, ok := avroSchema.(map[string]any); ok {
					contractEntry, _ := refactor_me(outputPortSchemaEntry) // todo error
					if fields, ok := contractEntry["fields"].([]any); ok && len(fields) != 0  {
						contractSchemaSpec = append(contractSchemaSpec, contractEntry)
					}
				}

			}
		}
	}
	// todo default copy schema and log that

	contractSchemaSpecBytes, err := json.Marshal(contractSchemaSpec)

	return &dataSourceSchema{outputPortSchemaType, contractSchemaSpecBytes}, err
}

func refactor_me(outputPortSchema map[string]any) (map[string]any, error) {
	columns := make(map[string][]string)

	fieldName := fmt.Sprintf("%v.%v", outputPortSchema["namespace"], outputPortSchema["name"])
	fields := outputPortSchema["fields"].([]any)
	columns[fieldName] = make([]string, len(fields))

	for i, field := range fields {
		columns[fieldName][i] = field.(map[string]any)["name"].(string)
	}

	allFieldNames := strings.Join(columns[fieldName], ",")

	input, err := prompt("Enter comma-seperated list of needed fields from output port. Enter '-' if no filed is needed.",
		&suggestion{allFieldNames, "all"})

	result := make(map[string]any)

	selectedFieldsSchema := make([]any, 0)

	if input != "-" {
		selectedFieldNames := strings.Split(input, ",")

		fmt.Println(err)

		for _, name := range selectedFieldNames {
			found := containsString(columns[fieldName], name)

			// todo error if not found
			fmt.Println(name, found)
		}

		selectedFieldsSchema = make([]any, 0)
		for _, field := range fields {
			if containsString(selectedFieldNames, field.(map[string]any)["name"].(string)) {
				selectedFieldsSchema = append(selectedFieldsSchema, field)
			}
		}
	}

	for k, v := range outputPortSchema {
		result[k] = v
	}

	result["fields"] = selectedFieldsSchema

	return result, nil
}

func containsString(columns []string, name string) bool {
	for _, s := range columns {
		if name == s {
			return true
		}
	}
	return false
}
