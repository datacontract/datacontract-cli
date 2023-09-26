package main

import (
	"fmt"
	"gopkg.in/yaml.v3"
	"io"
	"net/http"
)

func Diff(dataContractFileName string, stableContractUrl string, pathToType []string, pathToSpecification []string) error {
	localDataContractBytes, _ := ReadLocalDataContract(dataContractFileName)
	res, _ := fetchStableContract(stableContractUrl)
	stableDataContractBytes, _ := readStableContract(res)

	stableDataset, _ := getDataset(stableDataContractBytes, pathToType, pathToSpecification)
	localDataset, _ := getDataset(localDataContractBytes, pathToType, pathToSpecification)

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

func getDataset(dataContractBytes []byte, pathToType []string, pathToSpecification []string) (dataset *Dataset, err error) {
	dataContract, err := ParseDataContract(dataContractBytes)
	if err != nil {
		return nil, fmt.Errorf("failed parsing data contract: %w", err)
	}

	schemaType, localSchemaSpecification, err := ExtractSchemaSpecification(dataContract, pathToType, pathToSpecification)
	if err != nil {
		return nil, fmt.Errorf("failed extracting schema specification: %w", err)
	}

	schemaSpecificationBytes := schemaSpecificationAsString(localSchemaSpecification)
	dataset, err = ParseDataset(schemaType, schemaSpecificationBytes)
	if err != nil {
		return nil, fmt.Errorf("failed parsing dataset: %w", err)
	}

	return dataset, err
}

func schemaSpecificationAsString(schemaSpecification interface{}) []byte {
	var schemaSpecificationBytes []byte
	if str, isString := schemaSpecification.(string); isString {
		schemaSpecificationBytes = []byte(str)
	} else if mp, isMap := schemaSpecification.(map[string]interface{}); isMap {
		schemaSpecificationBytes, _ = yaml.Marshal(mp)
	}
	return schemaSpecificationBytes
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
