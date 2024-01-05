# Data Contract CLI

<p>
  <a href="https://github.com/datacontract/cli/actions/workflows/ci.yaml?query=branch%3Amain">
    <img alt="Test Workflow" src="https://img.shields.io/github/actions/workflow/status/datacontract/cli/ci.yaml?branch=main"></a>
  <a href="https://img.shields.io/github/stars/datacontract/cli">
    <img alt="Stars" src="https://img.shields.io/github/stars/datacontract/cli" /></a>
  <!-- <a href="https://github.com/datacontract/cli/graphs/contributors">
    <img alt="Contributors" src="https://img.shields.io/github/contributors/datacontract/cli" /></a>
  <a href="https://github.com/datacontract/cli/releases">
    <img alt="Downloads" src="https://img.shields.io/github/downloads/datacontract/cli/total" /></a>
  <a href="https://github.com/datacontract/cli/releases">
    <img  alt="Downloads of latest" src="https://img.shields.io/github/downloads/datacontract/cli/latest/total" /></a> -->
</p>

The `datacontract` CLI lets you work with your `datacontract.yaml` files locally, and in your CI pipeline. It uses the [data contract specification](https://datacontract.com/) to validate your data contracts and to check for backwards compatibility. The CLI is open source and written in Go. It is integrated with [Data Contract Studio](https://studio.datacontract.com/) to easily share and visualize your data contracts.

## Usage

`datacontract` usually works with the `datacontract.yaml` file in your current working directory. You can specify a different file with the `--file` option.

```bash
# create a new data contract
$ datacontract init

# lint the data contract
$ datacontract lint

# find differences to another version of the data contract
$ datacontract diff --with stable/datacontract.yaml

# fail pipeline on breaking changes
$ datacontract breaking --with stable/datacontract.yaml

# export model as dbt
$ datacontract model --format=dbt

# import dbt as model
$ datacontract model --format=dbt < my_dbt_model.yaml

# print run quality checks defined in your data contract
$ datacontract test

# print quality definitions
$ datacontract quality

# write quality definitions
$ datacontract quality --type=SodaCL < my_soda_definitions.yaml

# create standalone data contract by inlining reference data
$ datacontract inline > datacontract.standalone.yaml
```

## Installation

### Homebrew
```bash
brew install datacontract/brew/datacontract
```

### Download binary artifact

#### Using the command line

```bash
# download + unpack
curl -L https://github.com/datacontract/cli/releases/download/{VERSION}/datacontract-{VERSION}-{OS}-{ARCH}.tar.gz -o datacontract.tar.gz
tar -xf datacontract.tar.gz

# use it
./datacontract --help
```

**Make sure to fill the placeholders, depending on your system:**

| Placeholder | Description                                    |
|-------------|------------------------------------------------|
| VERSION     | datacontract CLI version (e.g. `v0.6.0`)       |
| OS          | your operating system (linux, windows, darwin) |
| ARCH        | your processor architecture (amd64, arm64)     |

#### Manually

- go to https://github.com/datacontract/cli/releases and download the artifact of the latest release depending on your operating system and cpu architecture
- decompress the file (tarball or zipfolder)
- open the folder in your terminal and use the application:
  ```bash
  ./datacontract --help
  ```

### Build from sources
```bash
# build
git clone https://github.com/datacontract/cli
cd cli
git checkout tags/{VERSION}
go build ./cmd/datacontract.go

# use it
./datacontract --help
```

## Documentation

```
NAME:
   datacontract - Manage your data contracts 📄

USAGE:
   datacontract [global options] command [command options] [arguments...]

VERSION:
   v0.6.0

AUTHOR:
   Stefan Negele <stefan.negele@innoq.com>

COMMANDS:
   init      create a new data contract
   lint      linter for the data contract
   model     import / export the data model of the data contract
   quality   when data is found in STDIN the command will insert its content into the quality section of your data contract, otherwise it will print the quality specification
   test      (soda core integration only) - run quality checks for the data contract
   open      save and open the data contract in Data Contract Studio
   diff      show differences of your local and a remote data contract
   breaking  detect breaking changes between your local and a remote data contract
   inline    inline all references specified with '$ref' notation and print the result to STDOUT
   help, h   Shows a list of commands or help for one command

GLOBAL OPTIONS:
   --help, -h     show help
   --version, -v  print the version
```

### Commands

#### init 
```
NAME:
   datacontract init - create a new data contract

USAGE:
   datacontract init [command options] [arguments...]

OPTIONS:
   --file value      location of the data contract, path or url (except init) (default: "datacontract.yaml")
   --from value      url of a template or data contract (default: "https://datacontract.com/datacontract.init.yaml")
   --overwrite-file  replace the existing datacontract.yaml (default: false)
   --help, -h        show help
```

#### lint
```
NAME:
   datacontract lint - linter for the data contract

USAGE:
   datacontract lint [command options] [arguments...]

OPTIONS:
   --file value    location of the data contract, path or url (except init) (default: "datacontract.yaml")
   --schema value  path or url of Data Contract Specification json schema (default: "https://datacontract.com/datacontract.schema.json")
   --help, -h      show help
```

#### test - (Soda Core integration only)
The Soda Core integration requires a Soda Core CLI installation, see https://docs.soda.io/soda-library/install.html

```
NAME:
   datacontract test - (soda core integration only) - run quality checks for the data contract

USAGE:
   datacontract test [command options] [arguments...]

OPTIONS:
   --file value                        location of the data contract, path or url (except init) (default: "datacontract.yaml")
   --quality-type-path value           definition of a custom path to the quality type in your data contract (default: "quality.type")
   --quality-specification-path value  definition of a custom path to the quality specification in your data contract (default: "quality.specification")
   --soda-datasource value             data source configured in Soda to run your quality checks against (default: "default")
   --soda-config value                 location of your soda configuration, falls back to user configuration
   --help, -h                          show help
```

#### open
```
NAME:
   datacontract open - save and open the data contract in Data Contract Studio

USAGE:
   datacontract open [command options] [arguments...]

OPTIONS:
   --file value  location of the data contract, path or url (except init) (default: "datacontract.yaml")
   --help, -h    show help
```


#### diff
```
NAME:
   datacontract diff - show differences of your local and a remote data contract

USAGE:
   datacontract diff [command options] [arguments...]

OPTIONS:
   --file value                       location of the data contract, path or url (except init) (default: "datacontract.yaml")
   --with value                       location (url or path) of the stable version of the data contract
   --models-path value                definition of a custom path to the schema specification in your data contract (default: "models")
   --schema-type-path value           DEPRECATED - definition of a custom path to the schema type in your data contract (default: "schema.type")
   --schema-specification-path value  DEPRECATED - definition of a custom path to the schema specification in your data contract (default: "schema.specification")
   --help, -h                         show help
```

#### breaking
```
NAME:
   datacontract breaking - detect breaking changes between your local and a remote data contract

USAGE:
   datacontract breaking [command options] [arguments...]

OPTIONS:
   --file value                       location of the data contract, path or url (except init) (default: "datacontract.yaml")
   --with value                       location (url or path) of the stable version of the data contract
   --models-path value                definition of a custom path to the schema specification in your data contract (default: "models")
   --schema-type-path value           DEPRECATED - definition of a custom path to the schema type in your data contract (default: "schema.type")
   --schema-specification-path value  DEPRECATED - definition of a custom path to the schema specification in your data contract (default: "schema.specification")
   --help, -h                         show help
```

#### model

```
NAME:
   datacontract model - import / export the data model of the data contract

USAGE:
   datacontract model [command options] [arguments...]

DESCRIPTION:
   when data is found in STDIN the command will parse and insert its content into the models section of your data contract, otherwise it will print your data model

OPTIONS:
   --file value         location of the data contract, path or url (except init) (default: "datacontract.yaml")
   --models-path value  definition of a custom path to the schema specification in your data contract (default: "models")
   --format value       format of the model for input or output, valid options:
      - data-contract-specification
      - dbt
       (default: "data-contract-specification")
   --help, -h  show help
```

#### quality
```
NAME:
   datacontract quality - print quality checks of the data contract

USAGE:
   datacontract quality [command options] [arguments...]

OPTIONS:
   --file value                        location of the data contract, path or url (except init) (default: "datacontract.yaml")
   --quality-specification-path value  definition of a custom path to the quality specification in your data contract (default: "quality.specification")
   --help, -h                          show help
```

#### inline
```
NAME:
   datacontract inline - inline all references specified with '$ref' notation

USAGE:
   datacontract inline [command options] [arguments...]

OPTIONS:
   --file value  location of the data contract, path or url (except init) (default: "datacontract.yaml")
   --help, -h    show help
```

#### help
```
USAGE:
   datacontract help
```

## Contribution

We are happy to receive your contributions. Propose your change in an issue or directly create a pull request with your improvements.

## License

[MIT License](LICENSE)

## Credits

Created by [Stefan Negele](https://www.linkedin.com/in/stefan-negele-573153112/).
