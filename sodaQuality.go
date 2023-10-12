package main

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"io/ioutil"
	"log"
)

var sodaConfData = `
data_source duckdb_local:
  type: duckdb
  path: quality/db.duckdb
  read_only: true
`

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
	err = BrowseDir(qualityCheckDirName)
    if err != nil {
        return fmt.Errorf("The %v directory cannot be browsed: %v",
			qualityCheckDirName, err)
    }

	sodaConfDataAsBytes := []byte(sodaConfData)
	//log.Printf("YAML: %v\n", string(sodaConfData))
	
	err = ioutil.WriteFile(sodaConfFilepath, sodaConfDataAsBytes, 0)
	if err != nil {
		log.Fatal(err)
	}

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

