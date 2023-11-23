package datacontract

import (
	"os"
)

func Inline(dataContractLocation string) error {
	dataContract, err := GetDataContract(dataContractLocation)
	if err != nil {
		return err
	}

	err = InlineReferences(&dataContract, dataContract)
	if err != nil {
		return err
	}

	result, err := ToYaml(dataContract)
	if err != nil {
		return err
	}

	err = os.WriteFile(dataContractLocation, result, os.ModePerm)
	if err != nil {
		return err
	}

	return nil
}
