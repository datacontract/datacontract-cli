package datacontract

import (
	"log"
	"strings"
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

	log.Println(strings.TrimSpace(string(result)))

	return nil
}
