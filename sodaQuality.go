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

const sodaDBFilename = "db.duckdb"
const sodaDirName = "quality"

var sodaConfDataTmplt = `
data_source %s:
  type: duckdb
  path: %s
  read_only: true
`

type SodaOptions struct {
	Directory     string `names:"-D,-dir,--dir" usage:"location path of the directory for quality checks, storing locally the various required and generated files such as SodaCL configuration and/or DuckDB local database file" default:"quality"`
	Configuration string `names:"-c,-conf,--conf" usage:"configuration file, in YAML, for SodaCL" default:"quality/soda-conf.yml"`
	Database      string `names:"-d,-db,--db" usage:"underlying database for SodaCL" default:"duckdb_local"`
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

	// If no command-line option has been passed, makes it as if the quality
	// directory has been passed ("-D quality"). That is to avoid an error
	// with the flag module when the command-line option part is empty
	sodaOptionStr := fmt.Sprintf("-D %s", sodaDirName)
	if len(qualityCheckOptions) == 0 {
		qualityCheckOptions = sodaOptionStr
	}
	
	optionTmp := []string{"soda", qualityCheckOptions}
	options := strings.Join(optionTmp, " ")
	optionList := strings.Split(options, " ")
	flag.NewFlagSet(flag.Flag{}).ParseStruct(&soda, optionList...)

	//fmt.Printf("Configuration file: %s ; Database: %s ; Temporary directory: %s/\n", soda.Configuration, soda.Database, soda.Directory)

	return soda, nil
}

func sodaQualityInit(soda SodaOptions) (err error) {

	// Retrieve the parameters from the command-line option structure
	qualityCheckDirName := soda.Directory // Default: "quality"
	sodaConfFilepathStr := soda.Configuration // Default: "soda-conf.yml"
	sodaDB := soda.Database // Default: "duckdb_local"

	sodaConfFilepath := filepath.Join(sodaConfFilepathStr)
	sodaDBFilepath := filepath.Join(qualityCheckDirName, sodaDBFilename)
	sodaConfData := fmt.Sprintf(sodaConfDataTmplt, sodaDB, sodaDBFilepath)

	// Create the folder aimed at storing the Soda configuration and
	// DuckDB database file
	log.Printf("Creating '%s/' directory if needed...\n", qualityCheckDirName)
	err = os.MkdirAll(qualityCheckDirName, os.ModePerm)
    if err != nil {
        return fmt.Errorf("The %v directory cannot be created: %v",
			qualityCheckDirName, err)
    }

	// Check if the error is "file not exists"
	_ , errConfFile := os.Stat(sodaConfFilepath)
	if os.IsNotExist(errConfFile) {
		log.Printf("'%s' conf file does not exist and will be created\n",
			sodaConfFilepath)

		// Write a default Soda configuration if none is already existing
		sodaConfDataAsBytes := []byte(sodaConfData)
		err = ioutil.WriteFile(sodaConfFilepath, sodaConfDataAsBytes, 0664)
		if err != nil {
			return fmt.Errorf("The %v configuration file cannot be created: %v",
				sodaConfFilepath, err)
		}

		log.Printf("'%s' conf file has been created\n",	sodaConfFilepath)

	} else {
		log.Printf("'%s' conf file seems to exist already; all is fine so far\n",	sodaConfFilepath)
	}

	return nil
}

func sodaQualityCheck(
	qualitySpecFileName string,
	qualityCheckOptions string) (res string, err error) {

	// Parse the command-line options specific to the quality checks
	soda, _ := sodaParseOptions(qualityCheckOptions)
	log.Printf("Command line options for the quality checks - Configuration file: %s ; Database: %s ; Temporary directory: %s/\n", soda.Configuration, soda.Database, soda.Directory)


	// Initialize the environment, if needed
	err = sodaQualityInit(soda)

	// Retrieve the parameters from the command-line option structure
	sodaConfFilepathStr := soda.Configuration // Default: "soda-conf.yml"
	sodaDB := soda.Database // Default: "duckdb_local"

	sodaConfFilepath := filepath.Join(sodaConfFilepathStr)

	//
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

