package main

import (
	"os"
	"testing"
)

func TestInline(t *testing.T) {
	type args struct {
		dataContractLocation string
	}
	tests := []struct {
		name     string
		args     args
		wantErr  bool
		wantFile string
	}{
		{
			name:     "quality",
			args:     args{dataContractLocation: "test_resources/inline/quality_datacontract.yaml"},
			wantErr:  false,
			wantFile: "test_resources/inline/quality_datacontract_inlined.yaml",
		},
		{
			name:     "schema",
			args:     args{dataContractLocation: "test_resources/inline/schema_datacontract.yaml"},
			wantErr:  false,
			wantFile: "test_resources/inline/schema_datacontract_inlined.yaml",
		},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			tmpFile := CreateTmpFileName()
			input, _ := os.ReadFile(tt.args.dataContractLocation)
			os.WriteFile(tmpFile, input, os.ModePerm)

			if err := Inline(tmpFile); (err != nil) != tt.wantErr {
				t.Errorf("Inline() error = %v, wantErr %v", err, tt.wantErr)
			}

			generated, _ := os.ReadFile(tmpFile)
			expected, _ := os.ReadFile(tt.wantFile)

			if string(generated) != string(expected) {
				t.Errorf("Inline() gotFile = %v, wantFile %v", string(generated), string(expected))
			}
		})
	}
}
