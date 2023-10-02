package main

import (
	"fmt"
	"os"
	"reflect"
	"testing"
)

func TestGetValue(t *testing.T) {
	model, _ := os.ReadFile("./test_resources/model.yaml")

	type args struct {
		contract DataContract
		path     []string
	}
	tests := []struct {
		name      string
		args      args
		wantValue interface{}
		wantErr   bool
	}{
		{
			name: "found",
			args: args{
				contract: DataContract{"schema": map[string]interface{}{"type": "dbt"}},
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
				contract: DataContract{"schema": map[string]interface{}{}},
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
				contract: DataContract{"schema": map[string]interface{}{
					"specification": "$ref: test_resources/model.yaml",
				}},
				path: []string{"schema", "specification"}},
			wantValue: string(model),
			wantErr:   false,
		},
		{
			name: "remote reference",
			args: args{
				contract: DataContract{"schema": map[string]interface{}{
					"specification": fmt.Sprintf("$ref: %v/model.yaml", TestResourcesServer.URL),
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
