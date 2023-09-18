# datacontract.sh

## Commands

### init 
```
NAME:
   datacontract init - create a new data contract

USAGE:
   datacontract init [command options] [arguments...]

OPTIONS:
   --file value      file name for the data contract (default: "datacontract.yaml")
   --from value      url of a template or data contract (default: "https://datacontract.com/datacontract.init.yaml")
   --overwrite-file  replace the existing datacontract.yaml (default: false)
   --interactive     EXPERIMENTAL - prompt for required values (default: false)
   --help, -h        show help
```

### validate
```
NAME:
   datacontract validate - validates the data contracts schema

USAGE:
   datacontract validate [command options] [arguments...]

OPTIONS:
   --file value               file name for the data contract (default: "datacontract.yaml")
   --schema value             url of Data Contract Specification json schema (default: "https://datacontract.com/datacontract.schema.json")
   --validate-schema-object   EXPERIMENTAL - type specific validation of the schema object (default: false)
   --validate-quality-object  EXPERIMENTAL - type specific validation of the quality object (default: false)
   --help, -h                 show help
```

### open
```
NAME:
   datacontract open - save and open the data contract in Data Contract Studio

USAGE:
   datacontract open [command options] [arguments...]

OPTIONS:
   --file value  file name for the data contract (default: "datacontract.yaml")
   --help, -h    show help
```


### check-compatibility (EXPERIMENTAL)
```
NAME:
   datacontract check-compatibility - EXPERIMENTAL - determine whether changes are backwards compatible

USAGE:
   datacontract check-compatibility [command options] [arguments...]

OPTIONS:
   --file value  file name for the data contract (default: "datacontract.yaml")
   --with value  url of the other version of the data contract
   --help, -h    show help
```

### help
```
USAGE:
   datacontract help
```
