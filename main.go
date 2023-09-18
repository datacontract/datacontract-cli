package main

import (
	"github.com/urfave/cli/v2"
	"log"
	"os"
)

const dataContractFileName = "datacontract.yaml"
const initTemplateUrl = "https://datacontract.com/datacontract.init.yaml"
const schemaUrl = "https://datacontract.com/datacontract.schema.json"
const dataContractStudioUrl = "https://studio.datacontract.com/s"

func main() {
	app := &cli.App{
		Name:    "datacontract",
		Usage:   "Manage your data contracts 📜",
		Version: "1.0.0",
		Authors: []*cli.Author{
			{Name: "Stefan Negele", Email: "stefan.negele@innoq.com"},
		},
		Commands: []*cli.Command{
			{
				Name:  "init",
				Usage: "create a new data contract",
				Flags: []cli.Flag {
					&cli.StringFlag{
						Name: "url",
						Value: initTemplateUrl,
						Usage: "url of the init template",
					},
				},
				Action: func(ctx *cli.Context) error {
					return Init(dataContractFileName, ctx.String("url"))
				},
			},
			{
				Name:  "validate",
				Usage: "validates the data contracts schema",
				Action: func(*cli.Context) error {
					return Validate(dataContractFileName, schemaUrl)
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
