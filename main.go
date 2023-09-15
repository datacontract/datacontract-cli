package main

import (
	"github.com/urfave/cli/v2"
	"log"
	"os"
)

const dataContractFileName = "datacontract.yaml"
const initTemplateUrl = "https://datacontract.com/datacontract.init.yaml"
const dataContractStudioUrl = "https://studio.datacontract.com/s"

func main() {
	app := &cli.App{
		Name:  "datacontract",
		Usage: "Manage your data contracts 📜",
		Commands: []*cli.Command{
			{
				Name:  "init",
				Usage: "create a new data contract",
				Action: func(*cli.Context) error {
					return Init(dataContractFileName, initTemplateUrl)
				},
			},
			{
				Name:  "open",
				Usage: "open the data contract in Data Contract Studio",
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
