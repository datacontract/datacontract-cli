package main

import (
	"fmt"
	"os/exec"
	"log"
)

func QualityCheck(
	dataContractFileName string,
	qualityCheckFileName string) error {
	dataContract, err := GetDataContract(dataContractFileName)

	if err != nil {
		return fmt.Errorf("quality checks failed: %w", err)
	}

	return qualityCheck(dataContract)
}

func qualityCheck(contract DataContract) error {
	pathToType := []string{"quality", "type"}
	pathToSpecification := []string{"quality", "specification"}

	qualityType, err := getQualityType(contract, pathToType)
	if err != nil {
		return fmt.Errorf("quality type cannot be retrieved: %w", err)
	}

	qualitySpecification, err := getQualitySpecification(contract,
		pathToSpecification)	
	if err != nil {
		return fmt.Errorf("quality check specification cannot be retrieved: %w",
			err)
	}

	log.Printf("Quality type: %v - Quality specification: %v\n",
		qualityType, qualitySpecification)
	
    app := "soda"

    arg0 := "scan"
    arg1 := "-d"
    arg2 := "duckdb_local"
    arg3 := "-c"
    arg4 := "quality/soda-conf.yml"
    arg5 := "contracts/data-contract-flight-route-quality.yaml"

    cmd := exec.Command(app, arg0, arg1, arg2, arg3, arg4, arg5)
    stdout, err := cmd.Output()

    if err != nil {
        fmt.Println(err.Error())
        return nil
    }

    // Print the output
    fmt.Println(string(stdout))
	
	return nil
}

func PrintQuality(
	dataContractLocation string,
	qualityCheckFileName string,
	pathToQuality []string) error {
	dataContract, err := GetDataContract(dataContractLocation)
	if err != nil {
		return fmt.Errorf("failed parsing local data contract: %w", err)
	}

	qualitySpecification, err := getQualitySpecification(dataContract,
		pathToQuality)
	if err != nil {
		return fmt.Errorf("can't get specification: %w", err)
	}

	qualitySpecificationAsBytes := TakeStringOrMarshall(qualitySpecification)
	qualitySpecificationAsString := string(qualitySpecificationAsBytes)
	log.Println(qualitySpecificationAsString)

	return nil
}

func printQualityCheckState() {
	fmt.Println("🟢 quality checks on data contract passed!")
}

func getQualityType(
	contract DataContract,
	path []string) (qualityType string, err error) {
	qualityTypeUntyped, err := GetValue(contract, path)
	if err != nil {
		return "",
			fmt.Errorf("can't get value of quality type: %w for path %v",
				err, path)
	}

	qualityType, ok := qualityTypeUntyped.(string)
	if !ok {
		return "", fmt.Errorf("quality not of type string")
	}

	return qualityType, nil
}

func getQualitySpecification(
	contract DataContract,
	path []string) (specification interface{}, err error) {
	specification, err = GetValue(contract, path)
	if err != nil {
		return "",
			fmt.Errorf("can't get value of %w quality specification for path %v",
				err, path)
	}

	return specification, nil
}

