package datacontract

import (
	"errors"
	"fmt"
	"os"
	"os/exec"
	"path"
	"strings"
	"testing"
)

func TestPrintQuality(t *testing.T) {
	type args struct {
		dataContractLocation string
		pathToQuality        []string
	}
	tests := []LogOutputTest[args]{
		{
			name: "print",
			args: args{
				dataContractLocation: "test_resources/quality/datacontract-soda-embedded.yaml",
				pathToQuality:        []string{"quality", "specification"},
			},
			wantErr: false,
			wantOutput: `checks for my_table:
  - duplicate_count(order_id) = 0
`,
		},
	}
	for _, tt := range tests {
		RunLogOutputTest(t, tt, "PrintQuality", func() error {
			return PrintQuality(tt.args.dataContractLocation, tt.args.pathToQuality)
		})
	}
}

func TestInsertQuality(t *testing.T) {
	type args struct {
		dataContractLocation string
		qualitySpecification []byte
		qualityType          string
		pathToQuality        []string
		pathToType           []string
	}
	tests := []FileWriteTest[args]{
		{
			name: "insert",
			args: args{
				dataContractLocation: "test_resources/quality/InsertQuality/datacontract.yaml",
				qualitySpecification: []byte(`checks for my_table:
  - duplicate_count(order_id) = 0
`),
				qualityType:   "SodaCL",
				pathToQuality: []string{"quality", "specification"},
				pathToType:    []string{"quality", "type"},
			},
			wantErr:              false,
			expectedFileLocation: "test_resources/quality/InsertQuality/datacontract_inserted.yaml",
		},
	}
	for _, tt := range tests {
		RunFileWriteTest(t, tt, "InsertQuality", tt.args.dataContractLocation, func(tempFileName string) error {
			return InsertQuality(tempFileName, tt.args.qualitySpecification, tt.args.qualityType, tt.args.pathToQuality, tt.args.pathToType)
		})
	}
}

func TestQualityCheck_Soda_Output(t *testing.T) {
	type args struct {
		dataContractFileName string
		pathToType           []string
		pathToSpecification  []string
		options              QualityCheckOptions
	}
	tests := []LogOutputTest[args]{
		{
			name: "success",
			args: args{
				dataContractFileName: "test_resources/quality/datacontract-soda-embedded.yaml",
				pathToType:           []string{"quality", "type"},
				pathToSpecification:  []string{"quality", "specification"},
				options:              QualityCheckOptions{},
			},
			wantOutput: `output from soda
🟢 quality checks on data contract passed!
`,
		},
		{
			name: "error",
			args: args{
				dataContractFileName: "test_resources/quality/datacontract-soda-embedded.yaml",
				pathToType:           []string{"quality", "type"},
				pathToSpecification:  []string{"quality", "specification"},
				options:              QualityCheckOptions{},
			},
			wantErr: true,
			wantOutput: `output from soda
🔴 quality checks on data contract failed!
`,
		},
	}

	defer func() { cmdCombinedOutput = (*exec.Cmd).CombinedOutput }()

	for _, tt := range tests {
		cmdCombinedOutput = func(cmd *exec.Cmd) ([]byte, error) {
			if tt.name == "success" {
				return []byte("output from soda"), nil
			} else {
				return []byte("output from soda"), errors.New("checks failed")
			}
		}

		RunLogOutputTest(t, tt, "Diff", func() error {
			return QualityCheck(tt.args.dataContractFileName, tt.args.pathToType, tt.args.pathToSpecification, tt.args.options)
		})
	}
}

func TestQualityCheck_Soda_ChecksFileContent(t *testing.T) {
	type args struct {
		dataContractFileName string
		pathToType           []string
		pathToSpecification  []string
		options              QualityCheckOptions
	}
	tests := []struct {
		name            string
		args            args
		wantSodaArgs    []string
		wantErr         bool
		wantFileContent string
	}{
		{
			name: "embedded",
			args: args{
				dataContractFileName: "test_resources/quality/datacontract-soda-embedded.yaml",
				pathToType:           []string{"quality", "type"},
				pathToSpecification:  []string{"quality", "specification"},
				options:              QualityCheckOptions{},
			},
			wantFileContent: `checks for my_table:
  - duplicate_count(order_id) = 0
`,
		},
		{
			name: "referenced",
			args: args{
				dataContractFileName: "test_resources/quality/datacontract-soda-referenced.yaml",
				pathToType:           []string{"quality", "type"},
				pathToSpecification:  []string{"quality", "specification"},
				options:              QualityCheckOptions{},
			},
			wantFileContent: `checks for my_table:
  - duplicate_count(order_id) = 0
`,
		},
	}

	defer func() { cmdCombinedOutput = (*exec.Cmd).CombinedOutput }()

	for _, tt := range tests {
		cmdCombinedOutput = func(cmd *exec.Cmd) ([]byte, error) {
			bytes, _ := os.ReadFile(cmd.Args[len(cmd.Args)-1])
			if tt.wantFileContent != string(bytes) {
				return nil, fmt.Errorf("unwanted file content: \n%v", string(bytes))
			}
			return nil, nil
		}

		t.Run(tt.name, func(t *testing.T) {
			if err := QualityCheck(tt.args.dataContractFileName, tt.args.pathToType, tt.args.pathToSpecification, tt.args.options); (err != nil) != tt.wantErr {
				t.Errorf("QualityCheck() error = %v, wantErr %v", err, tt.wantErr)
			}
		})
	}
}

func TestQualityCheck_Soda_Arguments(t *testing.T) {
	otherDatasource := "duckdb_local"
	otherConfigurationFileName := "./my-soda-conf.yaml"

	type args struct {
		dataContractFileName string
		pathToType           []string
		pathToSpecification  []string
		options              QualityCheckOptions
	}
	tests := []struct {
		name         string
		args         args
		wantSodaArgs []string
		wantErr      bool
	}{
		{
			name: "with defaults",
			args: args{
				dataContractFileName: "test_resources/quality/datacontract-soda-embedded.yaml",
				pathToType:           []string{"quality", "type"},
				pathToSpecification:  []string{"quality", "specification"},
				options:              QualityCheckOptions{},
			},
			wantSodaArgs: []string{"soda", "scan", "-d", "default"},
		},
		{
			name: "with data source option",
			args: args{
				dataContractFileName: "test_resources/quality/datacontract-soda-embedded.yaml",
				pathToType:           []string{"quality", "type"},
				pathToSpecification:  []string{"quality", "specification"},
				options:              QualityCheckOptions{SodaDataSource: &otherDatasource},
			},
			wantSodaArgs: []string{"soda", "scan", "-d", otherDatasource},
		},
		{
			name: "with configuration file name option",
			args: args{
				dataContractFileName: "test_resources/quality/datacontract-soda-embedded.yaml",
				pathToType:           []string{"quality", "type"},
				pathToSpecification:  []string{"quality", "specification"},
				options:              QualityCheckOptions{SodaConfigurationFileName: &otherConfigurationFileName},
			},
			wantSodaArgs: []string{"soda", "scan", "-d", "default", "-c", otherConfigurationFileName},
		},
		{
			name: "with all soda options",
			args: args{
				dataContractFileName: "test_resources/quality/datacontract-soda-embedded.yaml",
				pathToType:           []string{"quality", "type"},
				pathToSpecification:  []string{"quality", "specification"},
				options: QualityCheckOptions{
					SodaDataSource:            &otherDatasource,
					SodaConfigurationFileName: &otherConfigurationFileName,
				},
			},
			wantSodaArgs: []string{"soda", "scan", "-d", otherDatasource, "-c", otherConfigurationFileName},
		},
	}

	defer func() { cmdCombinedOutput = (*exec.Cmd).CombinedOutput }()

	for _, tt := range tests {
		cmdCombinedOutput = mockSodaCLI(tt.wantSodaArgs)

		t.Run(tt.name, func(t *testing.T) {
			if err := QualityCheck(tt.args.dataContractFileName, tt.args.pathToType, tt.args.pathToSpecification, tt.args.options); (err != nil) != tt.wantErr {
				t.Errorf("QualityCheck() error = %v, wantErr %v", err, tt.wantErr)
			}
		})
	}
}

func mockSodaCLI(wantedArguments []string) func(cmd *exec.Cmd) (res []byte, err error) {
	return func(cmd *exec.Cmd) (res []byte, err error) {

		if len(wantedArguments) != len(cmd.Args)-1 {
			return nil, errors.New("unwanted soda argument length")
		}

		for i, actualArg := range wantedArguments[0:] {
			err = checkArgument(cmd, i, actualArg)
		}
		err = checkFileNameArgument(cmd)

		if err != nil {
			return nil, err
		}

		return []byte{}, nil
	}
}

func checkFileNameArgument(cmd *exec.Cmd) error {

	fileName := cmd.Args[len(cmd.Args)-1]
	expectedPrefix := path.Join(os.TempDir(), "quality-checks-")
	if !strings.HasPrefix(fileName, expectedPrefix) {
		return fmt.Errorf("unwanted quality checks filename argument: %v", fileName)
	}

	return nil
}

func checkArgument(cmd *exec.Cmd, position int, argument string) error {
	if cmd.Args[position] != argument {
		return fmt.Errorf("invalid argument %v on position %v", argument, position)
	}
	return nil
}
