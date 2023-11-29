package datacontract

import (
	"io"
)

func Inline(dataContractLocation string, target io.Writer) error {
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

	Log(target, string(result))

	return nil
}
