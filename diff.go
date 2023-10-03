package main

import (
	"fmt"
)

func Diff(dataContractFileName string, stableContractLocation string, pathToType []string, pathToSpecification []string) error {
	differences, err := GetDifferences(dataContractFileName, stableContractLocation, pathToType, pathToSpecification)
	if err != nil {
		return err
	}

	PrintDifferences(differences)

	return nil
}

func GetDifferences(
	dataContractLocation string,
	stableDataContractLocation string,
	pathToType []string,
	pathToSpecification []string,
) ([]DatasetDifference, error) {
	localDataContract, err := GetDataContract(dataContractLocation)
	if err != nil {
		return nil, fmt.Errorf("failed reading local data contract: %w", err)
	}

	stableDataContract, err := GetDataContract(stableDataContractLocation)
	if err != nil {
		return nil, fmt.Errorf("failed getting stable data contract: %w", err)
	}

	stableDataset, err := GetSchemaSpecification(localDataContract, pathToType, pathToSpecification)
	if err != nil {
		return nil, fmt.Errorf("failed getting schema specification for stable dataset: %w", err)
	}

	localDataset, err := GetSchemaSpecification(stableDataContract, pathToType, pathToSpecification)
	if err != nil {
		return nil, fmt.Errorf("failed getting schema specification for local dataset: %w", err)
	}

	differences := CompareDatasets(*stableDataset, *localDataset)
	return differences, nil
}

func PrintDifferences(differences []DatasetDifference) {
	fmt.Printf("Found %v differences between the data contracts!\n", len(differences))

	for i, difference := range differences {
		fmt.Println()
		fmt.Printf("%v Difference %v:\n", severityIcon(difference), i+1)
		fmt.Printf("Description:  %v\n", difference.Description)
		fmt.Printf("Type:         %v\n", difference.Type)
		fmt.Printf("Severity:     %v\n", difference.Severity)
		fmt.Printf("Level:        %v\n", difference.Level)
		if difference.ModelName != nil {
			fmt.Printf("Model:        %v\n", *difference.ModelName)
		}
		if difference.FieldName != nil {
			fmt.Printf("Field:        %v\n", *difference.FieldName)
		}
	}
}

func severityIcon(difference DatasetDifference) string {
	switch difference.Severity {
	case DatasetDifferenceSeverityInfo:
		return "🟡"
	case DatasetDifferenceSeverityBreaking:
		return "🔴"
	}

	return ""
}
