package cli

import (
	"fmt"
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

func sodaQualityInit(
	qualitySpecFileName string,
	qualityCheckDirName string) error {

	sodaConfFilepath := filepath.Join(qualityCheckDirName, sodaConfFilename)
	sodaDBFilepath := filepath.Join(qualityCheckDirName, sodaDBFilename)
	sodaConfData := fmt.Sprintf(sodaConfDataTmplt, sodaDB, sodaDBFilepath)

	// Create the folder aimed at storing the Soda configuration and
	// DuckDB database file
	log.Printf("Creating %v directory if needed...", qualityCheckDirName)
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
	qualityCheckDirName string) (res string, err error) {

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

