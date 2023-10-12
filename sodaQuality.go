package main

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"log"
	"database/sql"
	_ "github.com/marcboeker/go-duckdb"
)

var sodaConfData = `
data_source duckdb_local:
  type: duckdb
  path: quality/db.duckdb
  read_only: true
`

const duckdbFilename = "db.duckdb"

func duckdbDDL(qualityCheckDirName string) error {
	dbFilepath := filepath.Join(qualityCheckDirName, duckdbFilename)
	dbParams := "?access_mode=read_only"
	dbConnString := dbFilepath + dbParams

	// Connect to the DuckDB database
	db, err := sql.Open("duckdb", dbConnString)
	if err != nil {
		log.Fatal("Failed to connect to %s database: ", dbFilepath, err)
	}

	row := db.QueryRow("SELECT COUNT(*) from transport_routes")
	var count int64
	err = row.Scan(&count)
	log.Printf("Number of records in the transport_routes table in the %s database: %d\n", dbFilepath, count)
	
	defer db.Close()
	return nil
}

func sodaQualityInit(
	qualitySpecFileName string,
	qualityCheckDirName string) error {

	//sodaConfFilepath := filepath.Join(qualityCheckDirName, "soda-conf.yml")

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

	err = duckdbDDL(qualityCheckDirName)
    if err != nil {
        return fmt.Errorf("Issue with the DuckDB database - %v", err)
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

