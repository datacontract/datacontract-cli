package datacontract

import (
	"os"
)

func Inline(dataContractLocation string) error {
	dataContract, err := GetDataContract(dataContractLocation)
	if err != nil {
		return err
	}

	err = inlineReferences(&dataContract, dataContract)
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

func inlineReferences(item *map[string]any, contract DataContract) error {
	for key, field := range *item {

		if object, isObject := field.(map[string]any); isObject {
			inlineReferences(&object, contract)
		} else if list, isList := field.([]any); isList {
			for _, item := range list {
				if object, isObject := item.(map[string]any); isObject {
					inlineReferences(&object, contract)
				}
			}
		} else if IsReference(field) {
			value, err := ResolveReference(contract, field)
			if err != nil {
				return err
			}

			object := *item
			object[key] = value
		}
	}

	return nil
}
