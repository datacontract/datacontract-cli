package datacontract

import (
	"testing"
)

func TestBreaking(t *testing.T) {
	type args struct {
		dataContractLocation       string
		stableDataContractLocation string
		pathToType                 []string
		pathToSpecification        []string
	}
	tests := []LogOutputTest[args]{
		{
			name: "breaking",
			args: args{
				dataContractLocation:       "test_resources/breaking/dbt_breaking_datacontract.yaml",
				stableDataContractLocation: "test_resources/breaking/dbt_datacontract.yaml",
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
Model:        my_table
Field:        my_column
`,
		},
		{
			name: "not-breaking",
			args: args{
				dataContractLocation:       "test_resources/breaking/dbt_not_breaking_datacontract.yaml",
				stableDataContractLocation: "test_resources/breaking/dbt_datacontract.yaml",
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
			return Breaking(tt.args.dataContractLocation, tt.args.stableDataContractLocation, tt.args.pathToType, tt.args.pathToSpecification)
		})
	}
}
