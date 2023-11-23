package datacontract

import "testing"

func TestDiff(t *testing.T) {
	type args struct {
		dataContractLocation       string
		stableDataContractLocation string
		pathToModels               []string
		pathToType                 []string
		pathToSpecification        []string
	}
	tests := []LogOutputTest[args]{
		{
			name: "no model",
			args: args{
				dataContractLocation:       "test_resources/diff/datacontract_no_model.yaml",
				stableDataContractLocation: "test_resources/diff/datacontract_no_model.yaml",
				pathToModels:               []string{"models"},
				pathToType:                 []string{"schema", "type"},
				pathToSpecification:        []string{"schema", "specification"},
			},
			wantErr: false,
			wantOutput: `Found 0 differences between the data contracts!
`,
		},
		{
			name: "breaking - spec model",
			args: args{
				dataContractLocation:       "test_resources/diff/breaking_datacontract.yaml",
				stableDataContractLocation: "test_resources/diff/datacontract.yaml",
				pathToModels:               []string{"models"},
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
InternalModel:        my_table
InternalField:        my_column

🟡 Difference 2:
Description:  field 'my_table.my_column_2' was added
Type:         field-added
Severity:     info
Level:        field
InternalModel:        my_table
InternalField:        my_column_2
`,
		},
		{
			name: "not-breaking - spec model",
			args: args{
				dataContractLocation:       "test_resources/diff/not_breaking_datacontract.yaml",
				stableDataContractLocation: "test_resources/diff/datacontract.yaml",
				pathToModels:               []string{"models"},
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
InternalModel:        my_table
InternalField:        my_column_2
`,
		},
		{
			name: "two fields, 1 type-changed - spec model",
			args: args{
				dataContractLocation:       "test_resources/diff/two_fields_datacontract.yaml",
				stableDataContractLocation: "test_resources/diff/two_fields_stable_datacontract.yaml",
				pathToModels:               []string{"models"},
				pathToType:                 []string{"schema", "type"},
				pathToSpecification:        []string{"schema", "specification"},
			},
			wantErr: false,
			wantOutput: `Found 1 differences between the data contracts!

🔴 Difference 1:
Description:  type of field 'my_table.my_column' was changed from 'text' to 'timestamp'
Type:         field-type-changed
Severity:     breaking
Level:        field
InternalModel:        my_table
InternalField:        my_column
`,
		},
		{
			name: "breaking - dbt model",
			args: args{
				dataContractLocation:       "test_resources/diff/dbt_breaking_datacontract.yaml",
				stableDataContractLocation: "test_resources/diff/dbt_datacontract.yaml",
				pathToModels:               []string{"models"},
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
InternalModel:        my_table
InternalField:        my_column

🟡 Difference 2:
Description:  field 'my_table.my_column_2' was added
Type:         field-added
Severity:     info
Level:        field
InternalModel:        my_table
InternalField:        my_column_2
`,
		},
		{
			name: "not-breaking - dbt model",
			args: args{
				dataContractLocation:       "test_resources/diff/dbt_not_breaking_datacontract.yaml",
				stableDataContractLocation: "test_resources/diff/dbt_datacontract.yaml",
				pathToModels:               []string{"models"},
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
InternalModel:        my_table
InternalField:        my_column_2
`,
		},
		{
			name: "two fields, 1 type-changed - dbt model",
			args: args{
				dataContractLocation:       "test_resources/diff/dbt_two_fields_datacontract.yaml",
				stableDataContractLocation: "test_resources/diff/dbt_two_fields_stable_datacontract.yaml",
				pathToModels:               []string{"models"},
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
InternalModel:        awesome_feature_usage_history
InternalField:        my_column
`,
		},
		{
			name: "spec model + dbt model",
			args: args{
				dataContractLocation:       "test_resources/diff/datacontract.yaml",
				stableDataContractLocation: "test_resources/diff/dbt_datacontract.yaml",
				pathToModels:               []string{"models"},
				pathToType:                 []string{"schema", "type"},
				pathToSpecification:        []string{"schema", "specification"},
			},
			wantErr: false,
			wantOutput: `Found 1 differences between the data contracts!

🟡 Difference 1:
Description:  schema type changed from 'dbt' to 'data-contract-specification'
Type:         dataset-schema-type-changed
Severity:     info
Level:        dataset
`,
		},
	}
	for _, tt := range tests {
		RunLogOutputTest(t, tt, "Diff", func() error {
			return Diff(
				tt.args.dataContractLocation,
				tt.args.stableDataContractLocation,
				tt.args.pathToModels,
				tt.args.pathToType,
				tt.args.pathToSpecification,
			)
		})
	}
}
