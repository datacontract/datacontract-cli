package main

import (
	datacontract "github.com/datacontract/cli"
	"github.com/urfave/cli/v2"
	"log"
	"os"
	"strings"
)

const dataContractFileName = "datacontract.yaml"
const initTemplateUrl = "https://datacontract.com/datacontract.init.yaml"
const schemaUrl = "https://datacontract.com/datacontract.schema.json"
const dataContractStudioUrl = "https://studio.datacontract.com/s"

func main() {
	log.SetFlags(0)

	fileNameFlag := &cli.StringFlag{
		Name:  "file",
		Value: dataContractFileName,
		Usage: "location of the data contract, path or url (except init)",
	}

	modelsPathFlag := &cli.StringFlag{
		Name:  "models-path",
		Value: "models",
		Usage: "definition of a custom path to the schema specification in your data contract",
	}

	schemaTypePathFlag := &cli.StringFlag{
		Name:  "schema-type-path",
		Value: "schema.type",
		Usage: "DEPRECATED - definition of a custom path to the schema type in your data contract",
	}

	schemaSpecificationPathFlag := &cli.StringFlag{
		Name:  "schema-specification-path",
		Value: "schema.specification",
		Usage: "DEPRECATED - definition of a custom path to the schema specification in your data contract",
	}

	withFlag := &cli.StringFlag{
		Name:     "with",
		Required: true,
		Usage:    "location (url or path) of the stable version of the data contract",
	}

	qualityTypePathFlag := &cli.StringFlag{
		Name:  "quality-type-path",
		Value: "quality.type",
		Usage: "definition of a custom path to the quality type in your data contract",
	}

	qualitySpecificationPathFlag := &cli.StringFlag{
		Name:  "quality-specification-path",
		Value: "quality.specification",
		Usage: "definition of a custom path to the quality specification in your data contract",
	}

	app := &cli.App{
		Name:    "datacontract",
		Usage:   "Manage your data contracts 📄",
		Version: "v0.5.2",
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
				},
				Action: func(ctx *cli.Context) error {
					return datacontract.Init(ctx.String("file"), ctx.String("from"), ctx.Bool("overwrite-file"))
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
				},
				Action: func(ctx *cli.Context) error {
					return datacontract.Lint(ctx.String("file"), ctx.String("schema"), os.Stdout)
				},
			},
			{
				Name:  "model",
				Usage: "import / export the data model of the data contract",
				Description: "when data is found in STDIN the command will parse and insert its " +
					"content into the models section of your data contract, otherwise it will " +
					"print your data model",
				Flags: []cli.Flag{
					fileNameFlag,
					modelsPathFlag,
					&cli.StringFlag{
						Name:  "format",
						Value: datacontract.InternalModelSpecificationType,
						Usage: "format of the model for input or output, valid options:\n" +
							"- " + datacontract.InternalModelSpecificationType + "\n" +
							"- dbt \n",
					},
				},
				Action: func(ctx *cli.Context) error {
					pathToModels := parsePath(ctx, "models-path")

					// parse and insert model if something is in stdin
					stdin, err := readStdin()
					if err != nil {
						return err
					}
					if stdin != nil {
						return datacontract.InsertModel(ctx.String("file"), stdin, ctx.String("format"), pathToModels)
					}

					// print model
					return datacontract.PrintModel(ctx.String("file"), ctx.String("type"), pathToModels, os.Stdout)
				},
			},
			{
				Name:  "quality",
				Usage: "import / export the data model of the data contract",
				Description: "when data is found in STDIN the command will insert its content into the " +
					"quality section of your data contract, otherwise it will print the quality " +
					"specification",
				Flags: []cli.Flag{
					fileNameFlag,
					&cli.StringFlag{
						Name:  "type",
						Value: "custom",
						Usage: "definition of a custom path to the quality type in your data contract",
					},
					qualitySpecificationPathFlag,
					qualityTypePathFlag,
				},
				Action: func(ctx *cli.Context) error {
					pathToSpecification := parsePath(ctx, "quality-specification-path")
					pathToType := parsePath(ctx, "quality-type-path")

					// parse and insert quality specification if something is in stdin
					stdin, err := readStdin()
					if err != nil {
						return err
					}
					if stdin != nil {
						return datacontract.InsertQuality(ctx.String("file"), stdin, ctx.String("type"), pathToSpecification, pathToType)
					}

					// print quality specification
					return datacontract.PrintQuality(ctx.String("file"), pathToSpecification, os.Stdout)
				},
			},
			{
				Name:  "test",
				Usage: "(soda core integration only) - run quality checks for the data contract",
				Flags: []cli.Flag{
					fileNameFlag,
					qualityTypePathFlag,
					qualitySpecificationPathFlag,
					&cli.StringFlag{
						Name:  "soda-datasource",
						Value: "default",
						Usage: "data source configured in Soda to run your quality checks against",
					},
					&cli.StringFlag{
						Name:  "soda-config",
						Usage: "location of your soda configuration, falls back to user configuration",
					},
				},
				Action: func(ctx *cli.Context) error {
					pathToType := parsePath(ctx, "quality-type-path")
					pathToSpecification := parsePath(ctx, "quality-specification-path")

					sodaDataSource := ctx.String("soda-datasource")
					options := datacontract.QualityCheckOptions{SodaDataSource: &sodaDataSource}

					if ctx.String("soda-config") != "" {
						options.SodaConfigurationFileName = new(string)
						*options.SodaConfigurationFileName = ctx.String("soda-config")
					}

					return datacontract.QualityCheck(ctx.String("file"), pathToType, pathToSpecification, options, os.Stdout)
				},
			},
			{
				Name:  "open",
				Usage: "save and open the data contract in Data Contract Studio",
				Flags: []cli.Flag{fileNameFlag},
				Action: func(ctx *cli.Context) error {
					return datacontract.Open(ctx.String("file"), dataContractStudioUrl)
				},
			}, {
				Name:  "diff",
				Usage: "show differences of your local and a remote data contract",
				Flags: []cli.Flag{
					fileNameFlag,
					withFlag,
					modelsPathFlag,
					schemaTypePathFlag,
					schemaSpecificationPathFlag,
				},
				Action: func(ctx *cli.Context) error {
					pathToModels := parsePath(ctx, "models-path")
					pathToType := parsePath(ctx, "schema-type-path")
					pathToSpecification := parsePath(ctx, "schema-specification-path")

					return datacontract.Diff(ctx.String("file"), ctx.String("with"), pathToModels, pathToType, pathToSpecification, os.Stdout)
				},
			}, {
				Name:  "breaking",
				Usage: "detect breaking changes between your local and a remote data contract",
				Flags: []cli.Flag{
					fileNameFlag,
					withFlag,
					modelsPathFlag,
					schemaTypePathFlag,
					schemaSpecificationPathFlag,
				},
				Action: func(ctx *cli.Context) error {
					pathToModels := parsePath(ctx, "models-path")
					pathToType := parsePath(ctx, "schema-type-path")
					pathToSpecification := parsePath(ctx, "schema-specification-path")

					return datacontract.Breaking(ctx.String("file"), ctx.String("with"), pathToModels, pathToType, pathToSpecification, os.Stdout)
				},
			}, {
				Name:  "inline",
				Usage: "inline all references specified with '$ref' notation and print the result to STDOUT",
				Flags: []cli.Flag{fileNameFlag},
				Action: func(ctx *cli.Context) error {
					return datacontract.Inline(ctx.String("file"), os.Stdout)
				},
			},
		},
	}

	if err := app.Run(os.Args); err != nil {
		log.Printf("Exiting application with error: %v \n", err)
		os.Exit(1)
	}
}

func readStdin() ([]byte, error) {
	// check if anything in stdin, if not return nil
	stat, err := os.Stdin.Stat()
	if err != nil {
		return nil, err
	}
	if stat.Size() == 0 {
		return nil, err
	}

	// read stdin line by line
	var buffer []byte
	for {
		lineBuffer := make([]byte, 1024)
		size, err := os.Stdin.Read(lineBuffer)

		if size == 0 {
			break
		}

		if err != nil {
			return nil, err
		}

		buffer = append(buffer, lineBuffer[:size]...)
	}

	return buffer, nil
}

func parsePath(ctx *cli.Context, path string) []string {
	return strings.Split(ctx.String(path), ".")
}
