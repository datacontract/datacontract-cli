package cli

import (
	"fmt"
	"strings"
	"github.com/cosiner/flag"
	"os"
	"os/exec"
	"path/filepath"
	"io/ioutil"
	"log"
)

const sodaDB = "duckdb_local"
const sodaDBFilename = "db.duckdb"
const sodaConfFilename = "soda-conf.yml"

var sodaConfDataTmplt = `
data_source %s:
  type: duckdb
  path: %s
  read_only: true
`

type SodaOptions struct {
	Configuration string `names:"-c" usage:"configuration file, in YAML, for SodaCL"`
	Database      string `names:"-d" usage:"underlying database for SodaCL"`
}

func (t *SodaOptions) Metadata() map[string]flag.Flag {
	const (
		usage   = "soda is a tool for quality checks."
		version = "soda --version"
		desc = "command-line options for SodaCL"
	)
	return map[string]flag.Flag{
		"": {
			Usage:   usage,
			Version: version,
			Desc:    desc,
		},
	}
}

func sodaParseOptions(
	qualityCheckOptions string) (soda SodaOptions, err error) {

	optionTmp := []string{"soda", qualityCheckOptions}
	options := strings.Join(optionTmp, " ")
	optionList := strings.Split(options, " ")
	flag.NewFlagSet(flag.Flag{}).ParseStruct(&soda, optionList...)

	//fmt.Println(soda.Configuration)
	//fmt.Println(soda.Database)

	return soda, nil
}

func sodaQualityInit(
	qualitySpecFileName string,
	qualityCheckDirName string,
	qualityCheckOptions string) error {

	sodaConfFilepath := filepath.Join(qualityCheckDirName, sodaConfFilename)
	sodaDBFilepath := filepath.Join(qualityCheckDirName, sodaDBFilename)
	sodaConfData := fmt.Sprintf(sodaConfDataTmplt, sodaDB, sodaDBFilepath)

	sodaOptions, _ := sodaParseOptions(qualityCheckOptions)
	log.Printf("SodaCL command-line options: %s\n", sodaOptions)

	// Create the folder aimed at storing the Soda configuration and
	// DuckDB database file
	log.Printf("Creating %v directory if needed...\n", qualityCheckDirName)
	err := os.MkdirAll(qualityCheckDirName, os.ModePerm)
    if err != nil {
        return fmt.Errorf("The %v directory cannot be created: %v",
			qualityCheckDirName, err)
    }

	// Write the Soda configuration
	sodaConfDataAsBytes := []byte(sodaConfData)
	err = ioutil.WriteFile(sodaConfFilepath, sodaConfDataAsBytes, 0664)
	if err != nil {
		log.Fatal(err)
	}

	return nil
}

func sodaQualityCheck(
	qualitySpecFileName string,
	qualityCheckDirName string,
	qualityCheckOptions string) (res string, err error) {

	// Initialize the environment, if needed
	sodaQualityInit(qualitySpecFileName, qualityCheckDirName, qualityCheckOptions)

	sodaConfFilepath := filepath.Join(qualityCheckDirName, sodaConfFilename)

    app := "soda"

    arg0 := "scan"
    arg1 := "-d"
    arg2 := sodaDB
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

