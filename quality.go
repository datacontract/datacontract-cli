package main

import (
	"fmt"
	"os/exec"
	"log"
)

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

func QualityCheck(
	dataContractFileName string,
	qualityCheckFileName string,
	pathToType []string,
	pathToSpecification []string) error {

	// 
	contract, err := GetDataContract(dataContractFileName)
	if err != nil {
		return fmt.Errorf("quality checks failed: %w", err)
	}

	qualityType, err := getQualityType(contract, pathToType)
	if err != nil {
		return fmt.Errorf("quality type cannot be retrieved: %w", err)
	}

	if (qualityType != "SodaCL") {
		log.Printf("The '%v' quality type is not supported yet")
		return nil
	}

	qualitySpecification, err := getQualitySpecification(contract,
		pathToSpecification)	
	if err != nil {
		return fmt.Errorf("quality check specification cannot be retrieved: %w",
			err)
	}

	log.Printf("Quality specification:\n%v\n", qualitySpecification)

	res, err := sodaQualityCheck(qualityCheckFileName)

	// Log the output
    log.Println(string(res))

	return nil
}

func sodaQualityCheck(qualityCheckFileName string) (res string, err error) {
    app := "soda"

    arg0 := "scan"
    arg1 := "-d"
    arg2 := "duckdb_local"
    arg3 := "-c"
    arg4 := "quality/soda-conf.yml"
    arg5 := qualityCheckFileName

    cmd := exec.Command(app, arg0, arg1, arg2, arg3, arg4, arg5)

    stdout, err := cmd.Output()
    if err != nil {
        fmt.Println(err.Error())
        return res, nil
    }

	res = string(stdout)
	
	return res, nil
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

