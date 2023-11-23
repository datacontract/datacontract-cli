package datacontract

import "fmt"

func Breaking(
	dataContractLocation string,
	stableDataContractLocation string,
	pathToModels, pathToType, pathToSpecification []string,
) error {
	all, err := GetDifferences(
		dataContractLocation,
		stableDataContractLocation,
		pathToModels,
		pathToType,
		pathToSpecification,
	)
	if err != nil {
		return err
	}

	breaking := breakingDifferences(all)

	PrintDifferences(breaking)

	if len(breaking) != 0 {
		return fmt.Errorf("found breaking differences between the data contracts")
	}

	return nil
}

func breakingDifferences(allDifferences []ModelDifference) []ModelDifference {
	var breakingDifferences []ModelDifference
	for _, difference := range allDifferences {
		if difference.Severity == ModelDifferenceSeverityBreaking {
			breakingDifferences = append(breakingDifferences, difference)
		}
	}
	return breakingDifferences
}
