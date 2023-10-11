package main

import "testing"

func TestPrintQuality(t *testing.T) {
	type args struct {
		dataContractLocation string
		pathToQuality        []string
	}
	tests := []LogOutputTest[args]{
		{
			name: "print",
			args: args{
				dataContractLocation: "test_resources/quality/datacontract.yaml",
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
