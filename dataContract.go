package main

import (
	"fmt"
	"gopkg.in/yaml.v3"
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
