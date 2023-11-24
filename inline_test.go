package datacontract

import (
	"testing"
)

func TestInline(t *testing.T) {
	type args struct {
		dataContractLocation string
	}
	tests := []FileWriteTest[args]{
		{
			name:                 "quality",
			args:                 args{dataContractLocation: "test_resources/inline/quality_datacontract.yaml"},
			wantErr:              false,
			expectedFileLocation: "test_resources/inline/quality_datacontract_inlined.yaml",
		},
		{
			name:                 "schema",
			args:                 args{dataContractLocation: "test_resources/inline/schema_datacontract.yaml"},
			wantErr:              false,
			expectedFileLocation: "test_resources/inline/schema_datacontract_inlined.yaml",
		},
	}
	for _, tt := range tests {
		RunFileWriteTest(t, tt, "Inline", tt.args.dataContractLocation, func(tempFileName string) error { return Inline(tempFileName) })
	}
}
