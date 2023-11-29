package datacontract

import (
	"fmt"
	"io"
)

func Diff(
	dataContractLocation string,
	stableDataContractLocation string,
	pathToModels, pathToType, pathToSpecification []string,
	target io.Writer,
) error {
	differences, err := GetDifferences(
		dataContractLocation,
		stableDataContractLocation,
		pathToModels,
		pathToType,
		pathToSpecification,
	)
	if err != nil {
		return err
	}

	PrintDifferences(differences, target)

	return nil
}

func GetDifferences(
	dataContractLocation string,
	stableDataContractLocation string,
	pathToModels []string,
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

	stableDataset, err := getModelSpecification(stableDataContract, pathToModels, pathToType, pathToSpecification)
	if err != nil {
		return nil, fmt.Errorf("failed getting schema specification for stable dataset: %w", err)
	}

	localDataset, err := getModelSpecification(localDataContract, pathToModels, pathToType, pathToSpecification)
	if err != nil {
		return nil, fmt.Errorf("failed getting schema specification for local dataset: %w", err)
	}

	differences := CompareModelSpecifications(*stableDataset, *localDataset)
	return differences, nil
}

func getModelSpecification(
	contract DataContract,
	pathToModels []string,
	pathToSchemaType []string,
	pathToSchemaSpecification []string,
) (*InternalModelSpecification, error) {
	dataset, err := GetModelsFromSpecification(contract, pathToModels)
	if dataset == nil {
		dataset, err = GetModelSpecificationFromSchema(contract, pathToSchemaType, pathToSchemaSpecification)
	}
	if dataset == nil {
		dataset = &InternalModelSpecification{
			Type:   "none",
			Models: []InternalModel{},
		}
	}

	return dataset, err
}

func PrintDifferences(differences []ModelDifference, target io.Writer) {
	Log(target, "Found %v differences between the data contracts!\n", len(differences))

	for i, difference := range differences {
		Log(target, "\n")
		Log(target, "%v Difference %v:\n", severityIcon(difference), i+1)
		Log(target, "Description:  %v\n", difference.Description)
		Log(target, "Type:         %v\n", difference.Type)
		Log(target, "Severity:     %v\n", difference.Severity)
		Log(target, "Level:        %v\n", difference.Level)
		if difference.ModelName != nil {
			Log(target, "InternalModel:        %v\n", *difference.ModelName)
		}
		if difference.FieldName != nil {
			Log(target, "InternalField:        %v\n", *difference.FieldName)
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
