package datacontract

import (
	"context"
	"encoding/json"
	"fmt"
	"github.com/qri-io/jsonschema"
	"io"
	"log"
	"net/http"
)

func Lint(dataContractLocation string, schemaUrl string) error {
	schemaResponse, err := fetchSchema(schemaUrl)
	schemaData, err := readSchema(schemaResponse)
	schema, err := parseSchema(schemaData)

	dataContract, err := GetDataContract(dataContractLocation)

	if err != nil {
		return fmt.Errorf("linting failed: %w", err)
	}

	return lint(schema, dataContract)
}

func lint(schema *jsonschema.Schema, contract DataContract) error {
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
		log.Println("🟢 data contract is valid!")
	} else {
		log.Println("🔴 data contract is invalid, found the following errors:")
	}

	for i, keyError := range *validationState.Errs {
		log.Println(fmt.Sprintf("%v) %v", i+1, keyError.Message))
	}
}

func parseSchema(schemaData []byte) (*jsonschema.Schema, error) {
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
