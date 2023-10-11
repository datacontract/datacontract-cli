package main

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"log"
)

func PrintQuality(
	dataContractLocation string,
	qualitySpecFileName string,
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

func QualityInit(
	dataContractFileName string,
	qualitySpecFileName string,
	qualityCheckDirName string,
	pathToType []string,
	pathToSpecification []string) error {

	// 
	contract, err := GetDataContract(dataContractFileName)
	if err != nil {
		return fmt.Errorf("Cannot retrieve the data contract: %w", err)
	}

	qualityType, err := getQualityType(contract, pathToType)
	if err != nil {
		return fmt.Errorf("Cannot retrieve the quality type: %w", err)
	}

	if (qualityType != "SodaCL") {
		log.Printf("The '%v' quality type is not supported yet")
		return nil
	}

	err = sodaQualityInit(qualitySpecFileName, qualityCheckDirName)
	if err != nil {
		return fmt.Errorf("Initialization for quality checks failed: %w", err)
	}

	return nil
}

func QualityCheck(
	dataContractFileName string,
	qualitySpecFileName string,
	qualityCheckDirName string,
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

	res, err := sodaQualityCheck(qualitySpecFileName, qualityCheckDirName)

	// Log the output
    log.Println(string(res))

	return nil
}


func sodaQualityInit(
	qualitySpecFileName string,
	qualityCheckDirName string) error {

	sodaConfFilepath := filepath.Join(qualityCheckDirName, "soda-conf.yml")

	// Create the folder aimed at storing the Soda configuration and
	// DuckDB database file
	log.Printf("Creating %v directory if needed...", qualityCheckDirName)
	err := os.MkdirAll(qualityCheckDirName, os.ModePerm)
    if err != nil {
        return fmt.Errorf("The %v directory cannot be created: %v",
			qualityCheckDirName, err)
    }

	// Display the content of the directory
	err = filepath.Walk(qualityCheckDirName,
		func(path string, info os.FileInfo, err error) error {
			if err != nil {
				fmt.Println(err)
				return err
			}
			log.Printf("isDir: %v; name: %s; size: %v\n",
				info.IsDir(), path, info.Size())
			return nil
		})
    if err != nil {
        return fmt.Errorf("The %v directory cannot browsed: %v",
			qualityCheckDirName, err)
    }

    app := "ls"

    arg0 := "-laFh"
    arg1 := string(sodaConfFilepath)
    arg2 := qualitySpecFileName

    cmd := exec.Command(app, arg0, arg1, arg2)

    stdout, err := cmd.Output()
    if err != nil {
        return fmt.Errorf("The CLI failed: %v", err)
    }

	res := string(stdout)
	log.Println(res)

	return nil
}

func sodaQualityCheck(
	qualitySpecFileName string,
	qualityCheckDirName string) (res string, err error) {

	sodaConfFilepath := filepath.Join(qualityCheckDirName, "soda-conf.yml")

    app := "soda"

    arg0 := "scan"
    arg1 := "-d"
    arg2 := "duckdb_local"
    arg3 := "-c"
    arg4 := string(sodaConfFilepath)
    arg5 := qualitySpecFileName

    cmd := exec.Command(app, arg0, arg1, arg2, arg3, arg4, arg5)

    stdout, err := cmd.Output()
    if err != nil {
        return res, fmt.Errorf("The CLI failed: %v", err)
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

