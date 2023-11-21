package datacontract

import (
	"fmt"
	"log"
)

func Diff(dataContractLocation string, stableDataContractLocation string, pathToType []string, pathToSpecification []string) error {
	differences, err := GetDifferences(dataContractLocation, stableDataContractLocation, pathToType, pathToSpecification)
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
) ([]ModelDifference, error) {
	localDataContract, err := GetDataContract(dataContractLocation)
	if err != nil {
		return nil, fmt.Errorf("failed reading local data contract: %w", err)
	}

	stableDataContract, err := GetDataContract(stableDataContractLocation)
	if err != nil {
		return nil, fmt.Errorf("failed getting stable data contract: %w", err)
	}

	stableDataset, err := GetModelSpecificationFromSchema(stableDataContract, pathToType, pathToSpecification)
	if err != nil {
		return nil, fmt.Errorf("failed getting schema specification for stable dataset: %w", err)
	}

	localDataset, err := GetModelSpecificationFromSchema(localDataContract, pathToType, pathToSpecification)
	if err != nil {
		return nil, fmt.Errorf("failed getting schema specification for local dataset: %w", err)
	}

	differences := CompareModelSpecifications(*stableDataset, *localDataset)
	return differences, nil
}

func PrintDifferences(differences []ModelDifference) {
	log.Printf("Found %v differences between the data contracts!\n", len(differences))

	for i, difference := range differences {
		log.Println()
		log.Printf("%v Difference %v:\n", severityIcon(difference), i+1)
		log.Printf("Description:  %v\n", difference.Description)
		log.Printf("Type:         %v\n", difference.Type)
		log.Printf("Severity:     %v\n", difference.Severity)
		log.Printf("Level:        %v\n", difference.Level)
		if difference.ModelName != nil {
			log.Printf("InternalModel:        %v\n", *difference.ModelName)
		}
		if difference.FieldName != nil {
			log.Printf("InternalField:        %v\n", *difference.FieldName)
		}
	}
}

func severityIcon(difference ModelDifference) string {
	switch difference.Severity {
	case ModelDifferenceSeverityInfo:
		return "🟡"
	case ModelDifferenceSeverityBreaking:
		return "🔴"
	}

	return ""
}
