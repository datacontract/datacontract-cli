package datacontract

import (
	"fmt"
	"os"
	"reflect"
	"testing"
)

func TestGetValue(t *testing.T) {
	model, _ := os.ReadFile("./test_resources/dataContract/getValue/model.yaml")

	type args struct {
		contract DataContract
		path     []string
	}
	tests := []struct {
		name      string
		args      args
		wantValue any
		wantErr   bool
	}{
		{
			name: "found",
			args: args{
				contract: DataContract{"schema": map[string]any{"type": "dbt"}},
				path:     []string{"schema", "type"}},
			wantValue: "dbt",
			wantErr:   false,
		},
		{
			name: "path not found",
			args: args{
				contract: DataContract{},
				path:     []string{"schema", "type"}},
			wantErr: true,
		},
		{
			name: "field not found",
			args: args{
				contract: DataContract{"schema": map[string]any{}},
				path:     []string{"schema", "type"}},
			wantErr: true,
		},
		{
			name: "field is no map",
			args: args{
				contract: DataContract{"schema": "type"},
				path:     []string{"schema", "type"}},
			wantErr: true,
		},
		{
			name: "local reference",
			args: args{
				contract: DataContract{"schema": map[string]any{
					"specification": "$ref: test_resources/dataContract/getValue/model.yaml",
				}},
				path: []string{"schema", "specification"}},
			wantValue: string(model),
			wantErr:   false,
		},
		{
			name: "remote reference",
			args: args{
				contract: DataContract{"schema": map[string]any{
					"specification": fmt.Sprintf("$ref: %v/dataContract/getValue/model.yaml", TestResourcesServer.URL),
				}},
				path: []string{"schema", "specification"}},
			wantValue: string(model),
			wantErr:   false,
		},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			gotValue, err := GetValue(tt.args.contract, tt.args.path)
			if (err != nil) != tt.wantErr {
				t.Errorf("GetValue() error = %v, wantErr %v", err, tt.wantErr)
				return
			}
			if !reflect.DeepEqual(gotValue, tt.wantValue) {
				t.Errorf("GetValue() gotValue = %v, want %v", gotValue, tt.wantValue)
			}
		})
	}
}

func TestGetDataContract(t *testing.T) {
	dataContract := DataContract{
		"dataContractSpecification": "0.9.0",
		"id":                        "my-data-contract-id",
		"info": map[string]any{
			"title":   "My Data Contract",
			"version": "0.0.1",
		},
	}
	type args struct {
		location string
	}
	tests := []struct {
		name                   string
		args                   args
		wantDataContractObject DataContract
		wantErr                bool
	}{
		{
			name:                   "local",
			args:                   args{location: "test_resources/dataContract/getDataContract/datacontract.yaml"},
			wantDataContractObject: dataContract,
		},
		{
			name:                   "remote",
			args:                   args{location: fmt.Sprintf("%v/dataContract/getDataContract/datacontract.yaml", TestResourcesServer.URL)},
			wantDataContractObject: dataContract,
		},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			gotDataContractObject, err := GetDataContract(tt.args.location)
			if (err != nil) != tt.wantErr {
				t.Errorf("GetDataContract() error = %v, wantErr %v", err, tt.wantErr)
				return
			}
			if !reflect.DeepEqual(gotDataContractObject, tt.wantDataContractObject) {
				t.Errorf("GetDataContract() gotDataContractObject = %v, want %v", gotDataContractObject, tt.wantDataContractObject)
			}
		})
	}
}
