package datacontract

import (
	"bytes"
	"testing"
)

func TestInline(t *testing.T) {
	type args struct {
		dataContractLocation string
	}
	tests := []LogOutputTest[args]{
		{
			name:    "quality",
			args:    args{dataContractLocation: "test_resources/inline/quality_datacontract.yaml"},
			wantErr: false,
			wantOutput: `dataContractSpecification: 0.9.2
id: my-data-contract-id
info:
  title: My Data Contract
  version: 0.0.1
quality:
  specification: |
    checks for my_table:
      - duplicate_count(order_id) = 0
  type: SodaCL
`,
		},
		{
			name:    "schema",
			args:    args{dataContractLocation: "test_resources/inline/schema_datacontract.yaml"},
			wantErr: false,
			wantOutput: `dataContractSpecification: 0.9.2
id: my-data-contract-id
info:
  title: My Data Contract
  version: 0.0.1
schema:
  specification: |
    version: 2
    models:
      - name: my_table
        description: "contains data"
        config:
          materialized: table
        columns:
          - name: my_column
            data_type: text
            description: "contains values"
  type: dbt
`,
		},
		{
			name:    "models",
			args:    args{dataContractLocation: "test_resources/inline/models_datacontract.yaml"},
			wantErr: false,
			wantOutput: `dataContractSpecification: 0.9.2
definitions:
  my_table:
    description: contains data
    fields:
      my_column:
        description: contains values
        type: text
    type: table
id: my-data-contract-id
info:
  title: My Data Contract
  version: 0.0.1
models:
  my_table:
    description: contains data
    fields:
      my_column:
        description: contains values
        type: text
    type: table
`,
		},
	}
	for _, tt := range tests {
		RunLogOutputTest(t, tt, "Inline", func(buffer *bytes.Buffer) error {
			return Inline(tt.args.dataContractLocation, buffer)
		})
	}
}
