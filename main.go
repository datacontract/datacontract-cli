package main

import (
	"github.com/urfave/cli/v2"
	"log"
	"os"
)

const dataContractFileName = "datacontract.yml"
const initTemplateUrl = "https://datacontract.com/datacontract.init.yaml"

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
		},
	}

	if err := app.Run(os.Args); err != nil {
		log.Fatal(err)
	}
}
