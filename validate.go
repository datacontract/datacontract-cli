package main

import (
	"context"
	"encoding/json"
	"fmt"
	"github.com/qri-io/jsonschema"
	"gopkg.in/yaml.v3"
	"io"
	"net/http"
	"os"
)

type dataContract = map[string]interface{}

func Validate(dataContractFileName string, schemaUrl string) error {
	schemaResponse, err := fetchSchema(schemaUrl)
	schemaData, err := readSchema(schemaResponse)
	schema, err := createSchema(schemaData)
	dataContractObject, err := readDataContract(dataContractFileName)

	if err != nil {
		return fmt.Errorf("validation failed: %w", err)
	}

	return validate(schema, dataContractObject)
}

func validate(schema *jsonschema.Schema, contract dataContract) error {
	validationState := schema.Validate(context.Background(), contract)
	printValidationState(validationState)

	if !validationState.IsValid() {
		return fmt.Errorf("%v error(s) found in data contract", len(*validationState.Errs))
	} else {
		return nil
	}
}

func printValidationState(validationState *jsonschema.ValidationState) {
	if validationState.IsValid() {
		fmt.Println("🟢 data contract is valid!")
	} else {
		fmt.Println("🔴 data contract is invalid, found the following errors:")
	}

	for i, keyError := range *validationState.Errs {
		fmt.Println(fmt.Sprintf("%v) %v", i+1, keyError.Message))
	}
}

func readDataContract(dataContractFileName string) (map[string]interface{}, error) {
	var dataContractObject map[string]interface{}

	dataContractFile, err := os.ReadFile(dataContractFileName)
	if err != nil {
		return nil, fmt.Errorf("failed to read data contract file: %w", err)
	}

	err = yaml.Unmarshal(dataContractFile, &dataContractObject)
	if err != nil {
		return nil, fmt.Errorf("failed to unmarshal data contract file: %w", err)
	}

	return dataContractObject, nil
}

func createSchema(schemaData []byte) (*jsonschema.Schema, error) {
	schema := &jsonschema.Schema{}
	if err := json.Unmarshal(schemaData, schema); err != nil {
		return nil, fmt.Errorf("failed to unmarshal schema: %w", err)
	}
	return schema, nil
}

func readSchema(response *http.Response) ([]byte, error) {
	defer response.Body.Close()

	if schemaData, err := io.ReadAll(response.Body); err != nil {
		return nil, fmt.Errorf("failed to read json schema: %w", err)
	} else {
		return schemaData, nil
	}
}

func fetchSchema(schemaUrl string) (*http.Response, error) {
	if response, err := http.Get(schemaUrl); err != nil {
		return nil, fmt.Errorf("failed to fetch json schema: %v", response.Status)
	} else {
		return response, nil
	}
}
