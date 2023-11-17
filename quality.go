package datacontract

import (
	"fmt"
	"log"
	"os"
	"os/exec"
)

func PrintQuality(dataContractLocation string, pathToQuality []string) error {

	dataContract, err := GetDataContract(dataContractLocation)
	if err != nil {
		return fmt.Errorf("failed parsing local data contract: %w", err)
	}

	qualitySpecification, err := getQualitySpecification(dataContract, pathToQuality)
	if err != nil {
		return fmt.Errorf("can't get specification: %w", err)
	}

	log.Println(string(qualitySpecification))

	return nil
}

type QualityCheckOptions struct {
	sodaDataSource            *string
	sodaConfigurationFileName *string
}

func QualityCheck(
	dataContractFileName string,
	pathToType []string,
	pathToSpecification []string,
	options QualityCheckOptions,
) error {

	contract, err := GetDataContract(dataContractFileName)
	if err != nil {
		return fmt.Errorf("quality checks failed: %w", err)
	}

	qualityType, err := getQualityType(contract, pathToType)
	if err != nil {
		return fmt.Errorf("quality type cannot be retrieved: %w", err)
	}

	if qualityType != "SodaCL" {
		log.Printf("The '%s' quality type is not supported yet", qualityType)
		return nil
	}

	qualitySpecification, err := getQualitySpecification(contract, pathToSpecification)
	if err != nil {
		return fmt.Errorf("quality check specification cannot be retrieved: %w",
			err)
	}

	tempFile, err := os.CreateTemp("", "quality-checks-")
	if err != nil {
		return fmt.Errorf("can not create temporary file for quality checks: %w", err)
	}

	tempFile.Write(qualitySpecification)

	res, err := sodaQualityCheck(tempFile.Name(), options)
	if err != nil {
		return fmt.Errorf("quality checks failed: %v", res)
	}

	// todo
	log.Println("Soda CLI output:")
	log.Println(res)

	printQualityCheckState()

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
	path []string) (specification []byte, err error) {
	spec, err := GetValue(contract, path)
	if err != nil {
		return []byte{},
			fmt.Errorf("can't get value of %w quality specification for path %v",
				err, path)
	}

	return TakeStringOrMarshall(spec), nil
}

func sodaQualityCheck(qualitySpecFileName string, options QualityCheckOptions) (res string, err error) {
	var args = []string{"scan"}

	args = append(args, "-d")
	if options.sodaDataSource != nil {
		args = append(args, *options.sodaDataSource)
	} else {
		args = append(args, "default")
	}

	if options.sodaConfigurationFileName != nil {
		args = append(args, "-c")
		args = append(args, *options.sodaConfigurationFileName)
	}

	args = append(args, qualitySpecFileName)

	cmd := exec.Command("soda", args...)

	stdout, err := cmd.Output()
	if err != nil {
		return res, fmt.Errorf("the CLI failed: %v", string(stdout))
	}

	res = string(stdout)

	return res, nil
}
