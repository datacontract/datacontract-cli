package main

import (
	"fmt"
	"io"
	"net/http"
)

func Diff(dataContractFileName string, stableContractUrl string, pathToType []string, pathToSpecification []string) error {
	localDataContractBytes, _ := ReadLocalDataContract(dataContractFileName)
	localDataContract, err := ParseDataContract(localDataContractBytes)
	if err != nil {
		return fmt.Errorf("failed parsing local data contract: %w", err)
	}

	res, _ := fetchStableContract(stableContractUrl)
	stableDataContractBytes, _ := readStableContract(res)
	stableDataContract, err := ParseDataContract(stableDataContractBytes)
	if err != nil {
		return fmt.Errorf("failed parsing local data contract: %w", err)
	}

	stableDataset, _ := GetSchemaSpecification(localDataContract, pathToType, pathToSpecification)
	localDataset, _ := GetSchemaSpecification(stableDataContract, pathToType, pathToSpecification)

	differences := CompareDatasets(*stableDataset, *localDataset)

	printDifferences(differences)

	return nil
}

func printDifferences(differences []DatasetDifference) {
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

func fetchStableContract(url string) (*http.Response, error) {
	if response, err := http.Get(url); err != nil {
		return nil, fmt.Errorf("failed to fetch data contract to compare with: %v", response.Status)
	} else {
		return response, nil
	}
}

func readStableContract(response *http.Response) ([]byte, error) {
	defer response.Body.Close()

	if otherContractData, err := io.ReadAll(response.Body); err != nil {
		return nil, fmt.Errorf("failed to read data contract to compare with: %w", err)
	} else {
		return otherContractData, nil
	}
}
