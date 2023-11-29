package datacontract

import (
	"fmt"
	"io"
)

func Breaking(
	dataContractLocation string,
	stableDataContractLocation string,
	pathToModels, pathToType, pathToSpecification []string,
	target io.Writer,
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

	PrintDifferences(breaking, target)

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
