package main

import (
	"fmt"
	"gopkg.in/yaml.v3"
	"io"
	"net/http"
	"os"
)

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
		return contract[fieldName], nil
	}

	next, ok := contract[fieldName].(map[string]interface{})
	if !ok {
		return nil, fmt.Errorf("can't follow path using field '%v', it's not a map", fieldName)
	}

	return GetValue(next, path[1:])
}

func FetchDataContract(url string) (result []byte, err error) {
	response, err := http.Get(url)
	if err != nil {
		return nil, fmt.Errorf("failed to fetch data contract to compare with: %v", response.Status)
	}

	defer response.Body.Close()

	if otherContractData, err := io.ReadAll(response.Body); err != nil {
		return nil, fmt.Errorf("failed to read data contract to compare with: %w", err)
	} else {
		return otherContractData, nil
	}
}
