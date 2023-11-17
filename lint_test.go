package datacontract

import (
	"fmt"
	"testing"
)

func TestLint(t *testing.T) {
	type args struct {
		dataContractLocation string
		schemaUrl            string
	}
	tests := []LogOutputTest[args]{
		{
			name: "valid",
			args: args{
				dataContractLocation: "test_resources/lint/valid_datacontract.yaml",
				schemaUrl:            fmt.Sprintf("%v/lint/schema.json", TestResourcesServer.URL),
			},
			wantErr: false,
			wantOutput: `🟢 data contract is valid!
`,
		},
		{
			name: "invalid",
			args: args{
				dataContractLocation: "test_resources/lint/invalid_datacontract.yaml",
				schemaUrl:            fmt.Sprintf("%v/lint/schema.json", TestResourcesServer.URL),
			},
			wantErr: true,
			wantOutput: `🔴 data contract is invalid, found the following errors:
1) "id" value is required
`,
		},
	}
	for _, tt := range tests {
		RunLogOutputTest(t, tt, "Lint", func() error {
			return Lint(tt.args.dataContractLocation, tt.args.schemaUrl)
		})
	}
}
