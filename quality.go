package main

import (
	"fmt"
)

func PrintQuality(dataContractLocation string, pathToQuality []string) error {
	dataContract, err := GetDataContract(dataContractLocation)
	if err != nil {
		return fmt.Errorf("failed parsing local data contract: %w", err)
	}

	qualitySpecification, err := getQualitySpecification(dataContract, pathToQuality)
	if err != nil {
		return fmt.Errorf("can't get specification: %w", err)
	}

	fmt.Println(string(TakeStringOrMarshall(qualitySpecification)))

	return nil
}

func getQualitySpecification(contract DataContract, path []string) (specification interface{}, err error) {
	specification, err = GetValue(contract, path)
	if err != nil {
		return "", fmt.Errorf("can't get value of quality specification: %w for path %v", err, path)
	}

	return specification, nil
}
