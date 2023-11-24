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

func SetValue(contract DataContract, path []string, value any) {
	applyOnField(
		contract,
		path,
		true,
		func(object map[string]any, fieldName string) (any, error) {
			object[fieldName] = value
			return nil, nil
		},
	)
}

func GetValue(contract DataContract, path []string) (value any, err error) {
	return applyOnField(
		contract,
		path,
		false,
		func(object map[string]any, fieldName string) (any, error) {
			field := object[fieldName]

			if field == nil {
				return nil, fmt.Errorf("no field named '%v'", fieldName)
			}

			if IsReference(field) {
				field, err = ResolveReference(contract, field)
				if err != nil {
					return nil, err
				}
			}

			return field, nil
		},
	)
}

func applyOnField(
	object map[string]any,
	path []string,
	pave bool,
	do func(object map[string]any, fieldName string) (any, error),
) (any, error) {
	if len(path) < 1 {
		return object, nil
	}

	fieldName := path[0]

	if object[fieldName] == nil && pave {
		object[fieldName] = map[string]any{}
	}

	if len(path) == 1 {
		return do(object, fieldName)
	}

	next, ok := object[fieldName].(map[string]any)
	if !ok {
		return nil, fmt.Errorf("can't follow path using field '%v', it's not a map", fieldName)
	}

	return applyOnField(next, path[1:], pave, do)
}
