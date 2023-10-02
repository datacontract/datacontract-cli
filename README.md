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

The `datacontract` CLI lets you work with your `datacontract.yaml` files locally, and in your CI pipeline. It uses the [data contract specification](https://datacontract.com/) to validate your data contracts and to check for backwards compatibility.

The CLI is open source and written in Go. It is integrated with [Data Contract Studio](https://studio.datacontract.com/) to easily share and visualize your data contracts.

## Usage

`datacontract` usually works with the `datacontract.yaml` file in your current working directory. You can specify a different file with the `--file` option.

```bash
# create a new data contract
$ datacontract init

# lint the data contract
$ datacontract lint

# open the data contract in Data Contract Studio
$ datacontract open

# find differences to another version of the data contract
$ datacontract diff --with stable/datacontract.yaml

# find breaking changes
$ datacontract breaking --with stable/datacontract.yaml

# print schema
$ datacontract schema

# print quality definitions
$ datacontract quality
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
| VERSION     | datacontract CLI version (e.g. `v0.2.0`)       |
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
go build -o datacontract

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
   v0.2.0

AUTHOR:
   Stefan Negele <stefan.negele@innoq.com>

COMMANDS:
   init      create a new data contract
   lint      linter for the data contract
   test      EXPERIMENTAL - run tests for the data contract
   open      save and open the data contract in Data Contract Studio
   diff      EXPERIMENTAL - show differences of your local and a remote data contract
   breaking  EXPERIMENTAL - detect breaking changes between your local and a remote data contract
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
   --interactive     EXPERIMENTAL - prompt for required values (default: false)
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
   --schema value  url of Data Contract Specification json schema (default: "https://datacontract.com/datacontract.schema.json")
   --lint-schema   EXPERIMENTAL - type specific linting of the schema object (default: false)
   --lint-quality  EXPERIMENTAL - type specific validation of the quality object (default: false)
   --help, -h      show help
```

#### test (EXPERIMENTAL)
```
NAME:
   datacontract test - EXPERIMENTAL - run tests for the data contract

USAGE:
   datacontract test [command options] [arguments...]

OPTIONS:
   --help, -h  show help
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


#### diff - EXPERIMENTAL (dbt specification only)
```
NAME:
   datacontract diff - EXPERIMENTAL (dbt specification only) - show differences of your local and a remote data contract

USAGE:
   datacontract diff [command options] [arguments...]

OPTIONS:
   --file value                       location of the data contract, path or url (except init) (default: "datacontract.yaml")
   --with value                       location (url or path) of the stable version of the data contract
   --schema-type-path value           definition of a custom path to the schema type in your data contract (default: "schema.type")
   --schema-specification-path value  definition of a custom path to the schema specification in your data contract (default: "schema.specification")
   --help, -h                         show help
```

#### breaking - EXPERIMENTAL (dbt specification only)
```
NAME:
   datacontract breaking - EXPERIMENTAL (dbt specification only) - detect breaking changes between your local and a remote data contract

USAGE:
   datacontract breaking [command options] [arguments...]

OPTIONS:
   --file value                       location of the data contract, path or url (except init) (default: "datacontract.yaml")
   --with value                       location (url or path) of the stable version of the data contract
   --schema-type-path value           definition of a custom path to the schema type in your data contract (default: "schema.type")
   --schema-specification-path value  definition of a custom path to the schema specification in your data contract (default: "schema.specification")
   --help, -h                         show help
```

#### schema
```
NAME:
   datacontract schema - print schema of the data contract

USAGE:
   datacontract schema [command options] [arguments...]

OPTIONS:
   --file value                       location of the data contract, path or url (except init) (default: "datacontract.yaml")
   --schema-specification-path value  definition of a custom path to the schema specification in your data contract (default: "schema.specification")
   --help, -h                         show help
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
