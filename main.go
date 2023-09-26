package main

import (
	"fmt"
	"github.com/urfave/cli/v2"
	"os"
	"strings"
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
		Version: "v0.1.1",
		Authors: []*cli.Author{
			{Name: "Stefan Negele", Email: "stefan.negele@innoq.com"},
		},
		Commands: []*cli.Command{
			{
				Name:  "init",
				Usage: "create a new data contract",
				Flags: []cli.Flag{
					fileNameFlag,
					&cli.StringFlag{
						Name:  "from",
						Value: initTemplateUrl,
						Usage: "url of a template or data contract",
					},
					&cli.BoolFlag{
						Name:  "overwrite-file",
						Value: false,
						Usage: "replace the existing " + dataContractFileName,
					},
					&cli.BoolFlag{
						Name:  "interactive",
						Value: false,
						Usage: "EXPERIMENTAL - prompt for required values",
					},
				},
				Action: func(ctx *cli.Context) error {
					boolOptionNotImplemented(ctx, "interactive")

					return Init(ctx.String("file"), ctx.String("from"), ctx.Bool("overwrite-file"))
				},
			},
			{
				Name:  "lint",
				Usage: "linter for the data contract",
				Flags: []cli.Flag{
					fileNameFlag,
					&cli.StringFlag{
						Name:  "schema",
						Value: schemaUrl,
						Usage: "url of Data Contract Specification json schema",
					},
					&cli.BoolFlag{
						Name:  "lint-schema",
						Value: false,
						Usage: "EXPERIMENTAL - type specific linting of the schema object",
					},
					&cli.BoolFlag{
						Name:  "lint-quality",
						Value: false,
						Usage: "EXPERIMENTAL - type specific validation of the quality object",
					},
				},
				Action: func(ctx *cli.Context) error {
					boolOptionNotImplemented(ctx, "lint-schema")
					boolOptionNotImplemented(ctx, "lint-quality")

					return Lint(ctx.String("file"), ctx.String("schema"))
				},
			}, {
				Name:  "test",
				Usage: "EXPERIMENTAL - run tests for the data contract",
				Action: func(ctx *cli.Context) error {
					fmt.Println("Command `test` not implemented yet!")
					return nil
				},
			},
			{
				Name:  "open",
				Usage: "save and open the data contract in Data Contract Studio",
				Flags: []cli.Flag{fileNameFlag},
				Action: func(ctx *cli.Context) error {
					return Open(ctx.String("file"), dataContractStudioUrl)
				},
			}, {
				Name:  "diff",
				Usage: "EXPERIMENTAL - show differences of your local and a remote data contract",
				Flags: []cli.Flag{
					fileNameFlag,
					&cli.StringFlag{
						Name:     "with",
						Required: true,
						Usage:    "url of the stable version of the data contract",
					},
					&cli.StringFlag{
						Name:  "schema-type-path",
						Value: "schema.type",
						Usage: "definition of a custom path to the schema type in your data contract",
					},
					&cli.StringFlag{
						Name:  "schema-specification-path",
						Value: "schema.specification",
						Usage: "definition of a custom path to the schema specification in your data contract",
					},
				},
				Action: func(ctx *cli.Context) error {
					pathToType := strings.Split(ctx.String("schema-type-path"), ".")
					pathToSpecification := strings.Split(ctx.String("schema-specification-path"), ".")

					return Diff(ctx.String("file"), ctx.String("with"), pathToType, pathToSpecification)
				},
			}, {
				Name:  "breaking",
				Usage: "EXPERIMENTAL - detect breaking changes between your local and a remote data contract",
				Flags: []cli.Flag{
					fileNameFlag,
					&cli.StringFlag{
						Name:     "with",
						Required: true,
						Usage:    "url of the stable version of the data contract",
					},
					&cli.StringFlag{
						Name:  "schema-type-path",
						Value: "schema.type",
						Usage: "definition of a custom path to the schema type in your data contract",
					},
					&cli.StringFlag{
						Name:  "schema-specification-path",
						Value: "schema.specification",
						Usage: "definition of a custom path to the schema specification in your data contract",
					},
				},
				Action: func(ctx *cli.Context) error {
					pathToType := strings.Split(ctx.String("schema-type-path"), ".")
					pathToSpecification := strings.Split(ctx.String("schema-specification-path"), ".")

					return Breaking(ctx.String("file"), ctx.String("with"), pathToType, pathToSpecification)
				},
			},
		},
	}

	if err := app.Run(os.Args); err != nil {
		fmt.Printf("Exiting application with error: %v \n", err)
		os.Exit(1)
	}
}

func boolOptionNotImplemented(ctx *cli.Context, name string) {
	if ctx.Bool(name) {
		fmt.Printf("Option `%v` not implemented yet!\n", name)
	}
}
