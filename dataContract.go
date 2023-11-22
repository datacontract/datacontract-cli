package datacontract

import (
	"fmt"
	"gopkg.in/yaml.v3"
	"io"
	"net/http"
	"os"
)

type DataContract = map[string]any

func GetDataContract(location string) (DataContract, error) {
	if IsURI(location) {
		return getRemoteDataContract(location)
	} else {
		return getLocalDataContract(location)
	}
}

func getLocalDataContract(dataContractFileName string) (DataContract, error) {
	if dataContractFile, err := os.ReadFile(dataContractFileName); err != nil {
		return nil, fmt.Errorf("failed to read data contract file: %w", err)
	} else {
		return parseDataContract(dataContractFile)
	}
}

func getRemoteDataContract(url string) (DataContract, error) {
	response, err := http.Get(url)
	defer response.Body.Close()

	if err != nil {
		return nil, fmt.Errorf("failed to fetch data contract to compare with: %v", response.Status)
	}

	if contractData, err := io.ReadAll(response.Body); err != nil {
		return nil, fmt.Errorf("failed to read data contract to compare with: %w", err)
	} else {
		return parseDataContract(contractData)
	}
}

func parseDataContract(data []byte) (dataContractObject DataContract, err error) {
	if err = yaml.Unmarshal(data, &dataContractObject); err != nil {
		return nil, fmt.Errorf("failed to unmarshal data contract file: %w", err)
	}

	return dataContractObject, nil
}

func GetValue(contract DataContract, path []string) (value any, err error) {
	return getValue(contract, contract, path)
}

func getValue(contract DataContract, object map[string]any, path []string) (any, error) {
	if len(path) < 1 {
		return contract, nil
	}

	fieldName := path[0]

	if object[fieldName] == nil {
		return nil, fmt.Errorf("no field named '%v'", fieldName)
	}

	if len(path) == 1 {
		return resolveValue(contract, object[fieldName])
	}

	next, ok := object[fieldName].(map[string]any)
	if !ok {
		return nil, fmt.Errorf("can't follow path using field '%v', it's not a map", fieldName)
	}

	return getValue(contract, next, path[1:])
}

func resolveValue(contract DataContract, value any) (out any, err error) {
	if IsReference(value) {
		value, err = ResolveReference(contract, value)
		if err != nil {
			return nil, err
		}
	}

	return value, nil
}
