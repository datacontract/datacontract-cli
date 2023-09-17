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

func Validate(dataContractFileName string) error {
	schemaResponse, err := fetchSchema()
	schemaData, err := readSchema(schemaResponse)
	schema, err := createSchema(schemaData)
	dataContractObject, err := readDataContract(dataContractFileName)

	if err != nil {
		return fmt.Errorf("validation failed: %w", err)
	}

	res := schema.Validate(context.Background(), dataContractObject)

	if res.IsValid() {
		fmt.Println("Data contract is valid!")
	}

	for _, keyError := range *res.Errs {
		fmt.Println(fmt.Sprintf("%v: %v", keyError.PropertyPath, keyError.Message))
	}

	return nil
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

func fetchSchema() (*http.Response, error) {
	if response, err := http.Get("https://datacontract.com/datacontract.schema.json"); err != nil {
		return nil, fmt.Errorf("failed to fetch json schema: %v", response.Status)
	} else {
		return response, nil
	}
}
