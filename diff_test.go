package datacontract

import "testing"

func TestDiff(t *testing.T) {
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
				dataContractLocation:       "test_resources/diff/dbt_breaking_datacontract.yaml",
				stableDataContractLocation: "test_resources/diff/dbt_datacontract.yaml",
				pathToType:                 []string{"schema", "type"},
				pathToSpecification:        []string{"schema", "specification"},
			},
			wantErr: false,
			wantOutput: `Found 2 differences between the data contracts!

🔴 Difference 1:
Description:  field 'my_table.my_column' was removed
Type:         field-removed
Severity:     breaking
Level:        field
Model:        my_table
Field:        my_column

🟡 Difference 2:
Description:  field 'my_table.my_column_2' was added
Type:         field-added
Severity:     info
Level:        field
Model:        my_table
Field:        my_column_2
`,
		},
		{
			name: "not-breaking",
			args: args{
				dataContractLocation:       "test_resources/diff/dbt_not_breaking_datacontract.yaml",
				stableDataContractLocation: "test_resources/diff/dbt_datacontract.yaml",
				pathToType:                 []string{"schema", "type"},
				pathToSpecification:        []string{"schema", "specification"},
			},
			wantErr: false,
			wantOutput: `Found 1 differences between the data contracts!

🟡 Difference 1:
Description:  field 'my_table.my_column_2' was added
Type:         field-added
Severity:     info
Level:        field
Model:        my_table
Field:        my_column_2
`,
		},
		{
			name: "type-changed",
			args: args{
				dataContractLocation:       "test_resources/diff/dbt_two_fields_datacontract.yaml",
				stableDataContractLocation: "test_resources/diff/dbt_two_fields_stable_datacontract.yaml",
				pathToType:                 []string{"schema", "type"},
				pathToSpecification:        []string{"schema", "specification"},
			},
			wantErr: false,
			wantOutput: `Found 1 differences between the data contracts!

🔴 Difference 1:
Description:  type of field 'awesome_feature_usage_history.my_column' was changed from 'string' to 'timestamp'
Type:         field-type-changed
Severity:     breaking
Level:        field
Model:        awesome_feature_usage_history
Field:        my_column
`,
		},
	}
	for _, tt := range tests {
		RunLogOutputTest(t, tt, "Diff", func() error {
			return Diff(tt.args.dataContractLocation, tt.args.stableDataContractLocation, tt.args.pathToType, tt.args.pathToSpecification)
		})
	}
}
