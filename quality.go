package main

import (
	"fmt"
	"gopkg.in/yaml.v3"
)

func QualityCheck(dataContractFileName string) error {
	dataContract, err := GetDataContract(dataContractFileName)

	if err != nil {
		return fmt.Errorf("quality checks failed: %w", err)
	}

	return qualityCheck(dataContract)
}

func qualityCheck(contract DataContract) error {
	// fmt.Println("contract: %v", contract)
	pathToType := []string{"quality", "type"}
	pathToSpecification := []string{"quality", "specification"}
	dataset, err := GetQualitySpecification(contract, pathToType, pathToSpecification)
	
	if err != nil {
		return fmt.Errorf("quality checks failed: %w", err)
	}

	fmt.Println("Data set: %s", dataset)
	
	return nil
}

func PrintQuality(dataContractLocation string, pathToQuality []string) error {
	dataContract, err := GetDataContract(dataContractLocation)
	if err != nil {
		return fmt.Errorf("failed parsing local data contract: %w", err)
	}

	qualitySpecification, err := getQualitySpecification(dataContract, pathToQuality)
	if err != nil {
		return fmt.Errorf("can't get specification: %w", err)
	}

	fmt.Println(string(TakeStringOrMarshall(qualitySpecification)))

	return nil
}

func printQualityCheckState() {
	fmt.Println("🟢 quality checks on data contract passed!")
}

func GetQualitySpecification(dataContract DataContract, pathToType []string, pathToSpecification []string) (dataset *Dataset, err error) {
	qualityType, localQualitySpecification, err := extractQualitySpecification(dataContract, pathToType, pathToSpecification)
	if err != nil {
		return nil, fmt.Errorf("failed extracting quality specification: %w", err)
	}
	//fmt.Println("local quality spec: %v", localQualitySpecification)
	
	qualitySpecificationBytes := qualitySpecificationAsString(localQualitySpecification)
	if qualityType == "SodaCL" {
		dataset = parseSodaDataset(qualitySpecificationBytes)
	} else {
		fmt.Println("The '%s' quality type is not recognized yet", qualityType)
	}

	return dataset, nil
}

func qualitySpecificationAsString(qualitySpecification interface{}) []byte {
	var qualitySpecificationBytes []byte
	if str, isString := qualitySpecification.(string); isString {
		qualitySpecificationBytes = []byte(str)
	} else if mp, isMap := qualitySpecification.(map[string]interface{}); isMap {
		qualitySpecificationBytes, _ = yaml.Marshal(mp)
	}
	return qualitySpecificationBytes
}

func extractQualitySpecification(
	contract DataContract,
	pathToType []string,
	pathToSpecification []string,
) (qualityType string, specification interface{}, err error) {
	qualityType, err = getQualityType(contract, pathToType)
	if err != nil {
		return "", "", fmt.Errorf("can't get quality type: %w", err)
	}

	specification, err = getQualitySpecification(contract, pathToSpecification)
	if err != nil {
		return "", nil, fmt.Errorf("can't get specification: %w", err)
	}

	return qualityType, specification, nil
}

func getQualityType(contract DataContract, path []string) (qualityType string, err error) {
	qualityTypeUntyped, err := GetValue(contract, path)
	if err != nil {
		return "", fmt.Errorf("can't get value of quality type: %w for path %v", err, path)
	}

	qualityType, ok := qualityTypeUntyped.(string)
	if !ok {
		return "", fmt.Errorf("quality not of type string")
	}

	return qualityType, nil
}

func getQualitySpecification(contract DataContract, path []string) (specification interface{}, err error) {
	specification, err = GetValue(contract, path)
	if err != nil {
		return "", fmt.Errorf("can't get value of quality specification: %w for path %v", err, path)
	}

	return specification, nil
}


// soda

type sodaSpecification struct {
	Models []sodaModel
}

type sodaModel struct {
	Name        string
	Description string
}

func parseSodaDataset(specification []byte) *Dataset {
	var res sodaSpecification

	yaml.Unmarshal(specification, &res)
	models := modelsFromSodaSpecification(res)

	return &Dataset{SchemaType: "soda", Models: models}
}

func modelsFromSodaSpecification(res sodaSpecification) (models []Model) {
	for _, model := range res.Models {
		models = append(models, Model{
			Name:        model.Name,
			Description: &model.Description,
		})
	}

	return models
}

