package main

import (
	"fmt"
	"gopkg.in/yaml.v3"
	"io"
	"net/http"
	"net/url"
	"os"
	"strings"
)

const referencePrefix = "$ref:"

type DataContract = map[string]interface{}

func ReadLocalDataContract(dataContractFileName string) (dataContractFile []byte, err error) {
	if dataContractFile, err = os.ReadFile(dataContractFileName); err != nil {
		return nil, fmt.Errorf("failed to read data contract file: %w", err)
	}

	return dataContractFile, nil
}

func ParseDataContract(data []byte) (dataContractObject DataContract, err error) {
	if err = yaml.Unmarshal(data, &dataContractObject); err != nil {
		return nil, fmt.Errorf("failed to unmarshal data contract file: %w", err)
	}

	return dataContractObject, nil
}

func GetValue(contract DataContract, path []string) (value interface{}, err error) {
	fieldName := path[0]

	if contract[fieldName] == nil {
		return nil, fmt.Errorf("no field named '%v'", fieldName)
	}

	if len(path) == 1 {
		return resolveValue(contract, fieldName)
	}

	next, ok := contract[fieldName].(map[string]interface{})
	if !ok {
		return nil, fmt.Errorf("can't follow path using field '%v', it's not a map", fieldName)
	}

	return GetValue(next, path[1:])
}

func resolveValue(object map[string]interface{}, fieldName string) (value interface{}, err error) {
	value = object[fieldName]

	if stringValue, isString := value.(string); isString && strings.HasPrefix(stringValue, referencePrefix) {
		reference := strings.Trim(strings.TrimPrefix(stringValue, referencePrefix), " ")

		value, err = resolveReference(reference)
		if err != nil {
			return nil, err
		}
	}

	return value, nil
}

func resolveReference(reference string) (_ string, err error) {
	var bytes []byte

	if isURI(reference) {
		bytes, err = resolveReferenceFromRemote(reference)
	} else {
		bytes, err = resolveReferenceLocally(reference)
	}

	if err != nil {
		return "", fmt.Errorf("can't resolve reference '%v': %w", reference, err)
	}

	return string(bytes), nil
}

func resolveReferenceLocally(reference string) ([]byte, error) {
	return os.ReadFile(reference)
}

func resolveReferenceFromRemote(reference string) ([]byte, error) {
	response, err := http.Get(reference)
	defer response.Body.Close()

	if err != nil {
		return nil, err
	}

	return io.ReadAll(response.Body)
}

func isURI(reference string) bool {
	_, err := url.ParseRequestURI(reference)
	return err == nil
}

func FetchDataContract(url string) (result []byte, err error) {
	response, err := http.Get(url)
	if err != nil {
		return nil, fmt.Errorf("failed to fetch data contract to compare with: %v", response.Status)
	}

	defer response.Body.Close()

	if contractData, err := io.ReadAll(response.Body); err != nil {
		return nil, fmt.Errorf("failed to read data contract to compare with: %w", err)
	} else {
		return contractData, nil
	}
}