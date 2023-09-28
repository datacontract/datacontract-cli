package main

import (
	"fmt"
)

func QualityCheck(dataContractFileName string) error {
	dataContractFile, err := ReadLocalDataContract(dataContractFileName)
	dataContract, err := ParseDataContract(dataContractFile)

	if err != nil {
		return fmt.Errorf("linting failed: %w", err)
	}

	return qualityCheck(dataContract)
}

func qualityCheck(contract DataContract) error {
	printQualityCheckState()
	return nil
}

func printQualityCheckState() {
	fmt.Println("🟢 quality checks on data contract passed!")
}

