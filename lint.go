package datacontract

import (
	"context"
	"encoding/json"
	"fmt"
	"github.com/qri-io/jsonschema"
	"io"
	"net/http"
	"os"
)

func getSchema(location string) (*jsonschema.Schema, error) {
	if IsURI(location) {
		return getRemoteSchema(location)
	} else {
		return getLocalSchema(location)
	}
}

func getLocalSchema(schemaFileName string) (*jsonschema.Schema, error) {
	if schemaFile, err := os.ReadFile(schemaFileName); err != nil {
		return nil, fmt.Errorf("failed to read schema file: %w", err)
	} else {
        schema, err := parseSchema(schemaFile)
        if err != nil {
            return nil, err
        }
        return schema, nil
    }
}

func getRemoteSchema(schemaUrl string) (*jsonschema.Schema, error) {
	schemaResponse, err := fetchSchema(schemaUrl)
	if err != nil {
		return nil, err
	}

	schemaData, err := readSchema(schemaResponse)
	if err != nil {
		return nil, err
	}

	schema, err := parseSchema(schemaData)
	if err != nil {
		return nil, err
	}

	return schema, nil
}

func Lint(dataContractLocation string, schemaUrl string, target io.Writer) error {
	schema, err := getSchema(schemaUrl)
	if err != nil {
		return err
	}

	dataContract, err := GetDataContract(dataContractLocation)
	if err != nil {
		return err
	}

	return lint(schema, dataContract, target)
}

func lint(schema *jsonschema.Schema, contract DataContract, target io.Writer) error {
	validationState := schema.Validate(context.Background(), contract)
	printValidationState(validationState, target)

	if !validationState.IsValid() {
		return fmt.Errorf("%v error(s) found in data contract", len(*validationState.Errs))
	} else {
		return nil
	}
}

func printValidationState(validationState *jsonschema.ValidationState, target io.Writer) {
	if validationState.IsValid() {
		Log(target, "🟢 data contract is valid!")
	} else {
		Log(target, "🔴 data contract is invalid, found the following errors:")
	}

	for i, keyError := range *validationState.Errs {
		Log(target, "%v) %v\n", i+1, keyError.Message)
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
