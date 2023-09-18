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
	fileNameFlag := &cli.StringFlag{
		Name:  "file",
		Value: dataContractFileName,
		Usage: "file name for the data contract",
	}

	app := &cli.App{
		Name:    "datacontract",
		Usage:   "Manage your data contracts 📄",
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
						Name: "template",
						Value: initTemplateUrl,
						Usage: "url of the init template",
					},
					fileNameFlag,
				},
				Action: func(ctx *cli.Context) error {
					return Init(ctx.String("file"), ctx.String("url"))
				},
			},
			{
				Name:  "validate",
				Usage: "validates the data contracts schema",
				Flags: []cli.Flag {
					&cli.StringFlag{
						Name: "schema",
						Value: schemaUrl,
						Usage: "url of Data Contract Specification json schema",
					},
					fileNameFlag,
				},
				Action: func(ctx *cli.Context) error {
					return Validate(ctx.String("file"), ctx.String("file"))
				},
			},
			{
				Name:  "open",
				Usage: "open the data contract in Data Contract Studio",
				Flags: []cli.Flag {fileNameFlag},
				Action: func(ctx *cli.Context) error {
					return Open(ctx.String("file"), dataContractStudioUrl)
				},
			},
		},
	}

	if err := app.Run(os.Args); err != nil {
		log.Fatal(err)
	}
}
