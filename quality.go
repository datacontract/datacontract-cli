package main

import (
	"fmt"
	"gopkg.in/yaml.v3"
)

func PrintQuality(dataContractFileName string, pathToQuality []string) error {
	dataContractBytes, err := ReadLocalDataContract(dataContractFileName)
	if err != nil {
		return fmt.Errorf("failed reading data contract: %w", err)
	}
	dataContract, err := ParseDataContract(dataContractBytes)
	if err != nil {
		return fmt.Errorf("failed parsing local data contract: %w", err)
	}

	qualitySpecification, err := getQualitySpecification(dataContract, pathToQuality)
	if err != nil {
		return fmt.Errorf("can't get specification: %w", err)
	}

	fmt.Println(string(qualitySpecificationAsString(qualitySpecification)))

	return nil
}

func qualitySpecificationAsString(qualitySpecification interface{}) []byte {
	var qualitySpecificationBytes []byte
	if str, isString := qualitySpecification.(string); isString {
		qualitySpecificationBytes = []byte(str)
	} else if mp, isMap := qualitySpecification.(map[string]interface{}); isMap {
		qualitySpecificationBytes, _ = yaml.Marshal(mp)
	}
	return qualitySpecificationBytes
}

func getQualitySpecification(contract DataContract, path []string) (specification interface{}, err error) {
	specification, err = GetValue(contract, path)
	if err != nil {
		return "", fmt.Errorf("can't get value of quality specification: %w for path %v", err, path)
	}

	return specification, nil
}
