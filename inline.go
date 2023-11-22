package datacontract

import (
	"os"
)

func Inline(dataContractLocation string) error {
	dataContract, err := GetDataContract(dataContractLocation)
	if err != nil {
		return err
	}

	err = inlineReferences(&dataContract)
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

func inlineReferences(dataContract *map[string]any) error {
	for key, field := range *dataContract {

		if object, isObject := field.(map[string]any); isObject {
			inlineReferences(&object)
		} else if list, isList := field.([]any); isList {
			for _, item := range list {
				if object, isObject := item.(map[string]any); isObject {
					inlineReferences(&object)
				}
			}
		} else if text, isText := field.(string); isText && IsReference(text) {
			value, err := ResolveReference(text)
			if err != nil {
				return err
			}

			object := *dataContract
			object[key] = value
		}
	}

	return nil
}
