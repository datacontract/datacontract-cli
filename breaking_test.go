package datacontract

import (
	"testing"
)

func TestBreaking(t *testing.T) {
	type args struct {
		dataContractLocation       string
		stableDataContractLocation string
		pathToModels               []string
		pathToType                 []string
		pathToSpecification        []string
	}
	tests := []LogOutputTest[args]{
		{
			name: "breaking",
			args: args{
				dataContractLocation:       "test_resources/breaking/breaking_datacontract.yaml",
				stableDataContractLocation: "test_resources/breaking/datacontract.yaml",
				pathToModels:               []string{"models"},
				pathToType:                 []string{"schema", "type"},
				pathToSpecification:        []string{"schema", "specification"},
			},
			wantErr: true,
			wantOutput: `Found 1 differences between the data contracts!

🔴 Difference 1:
Description:  field 'my_table.my_column' was removed
Type:         field-removed
Severity:     breaking
Level:        field
InternalModel:        my_table
InternalField:        my_column
`,
		},
		{
			name: "not-breaking",
			args: args{
				dataContractLocation:       "test_resources/breaking/not_breaking_datacontract.yaml",
				stableDataContractLocation: "test_resources/breaking/datacontract.yaml",
				pathToModels:               []string{"models"},
				pathToType:                 []string{"schema", "type"},
				pathToSpecification:        []string{"schema", "specification"},
			},
			wantErr: false,
			wantOutput: `Found 0 differences between the data contracts!
`,
		},
	}
	for _, tt := range tests {
		RunLogOutputTest(t, tt, "Breaking", func() error {
			return Breaking(
				tt.args.dataContractLocation,
				tt.args.stableDataContractLocation,
				tt.args.pathToModels,
				tt.args.pathToType,
				tt.args.pathToSpecification,
			)
		})
	}
}
