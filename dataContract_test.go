package main

import (
	"reflect"
	"testing"
)

func TestGetValue(t *testing.T) {
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
