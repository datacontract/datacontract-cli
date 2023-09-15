package main

import (
	"github.com/urfave/cli/v2"
	"log"
	"os"
)

func main() {
	app := &cli.App{
		Name:  "datacontract",
		Usage: "Manage your data contracts 📜",
		Commands: []*cli.Command{
			{
				Name:  "init",
				Usage: "create the data contract template file",
				Action: func(*cli.Context) error {
					return Init()
				},
			},
		},
	}

	if err := app.Run(os.Args); err != nil {
		log.Fatal(err)
	}
}
