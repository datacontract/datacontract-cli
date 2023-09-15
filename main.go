package main

import (
	"github.com/urfave/cli/v2"
	"log"
	"os"
)

const dataContractFileName = "datacontract.yml"
const initTemplateUrl = "https://datacontract.com/datacontract.init.yaml"
const dataContractStudioUrl = "https://studio.datacontract.com/s"

func main() {
	app := &cli.App{
		Name:  "datacontract",
		Usage: "Manage your data contracts 📜",
		Commands: []*cli.Command{
			{
				Name:  "init",
				Usage: "create the data contract template file",
				Action: func(*cli.Context) error {
					return Init(dataContractFileName, initTemplateUrl)
				},
			},
			{
				Name:  "open",
				Usage: "upload and open the datacontract in Data Contract Studio",
				Action: func(*cli.Context) error {
					return Open(dataContractFileName, dataContractStudioUrl)
				},
			},
		},
	}

	if err := app.Run(os.Args); err != nil {
		log.Fatal(err)
	}
}
