package datacontract

import (
	"fmt"
	"os"
	"reflect"
	"testing"
)

func TestGetValue(t *testing.T) {
	stringReferenceModel, _ := os.ReadFile("./test_resources/dataContract/getValue/dbt_model.yaml")

	objectReferenceModelName := "myModel"
	objectReferenceModelDescription := "my model description"
	objectReferenceModelType := "table"
	objectReferenceFieldName := "my_id"
	objectReferenceFieldType := "int"
	objectReferenceFieldDescription := "my field description"

	objectReferenceModelDefinition := map[string]any{
		"description": objectReferenceModelDescription,
		"type":        objectReferenceModelType,
		"fields": map[string]any{
			objectReferenceFieldName: map[string]any{
				"type":        objectReferenceFieldType,
				"description": objectReferenceFieldDescription,
			},
		},
	}

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
			name: "local string reference",
			args: args{
				contract: DataContract{"schema": map[string]any{
					"specification": "$ref: test_resources/dataContract/getValue/dbt_model.yaml",
				}},
				path: []string{"schema", "specification"}},
			wantValue: string(stringReferenceModel),
			wantErr:   false,
		},
		{
			name: "remote string reference",
			args: args{
				contract: DataContract{"schema": map[string]any{
					"specification": fmt.Sprintf("$ref: %v/dataContract/getValue/dbt_model.yaml", TestResourcesServer.URL),
				}},
				path: []string{"schema", "specification"}},
			wantValue: string(stringReferenceModel),
			wantErr:   false,
		},
		{
			name: "definitions object reference",
			args: args{
				contract: DataContract{
					"models": map[string]any{
						objectReferenceModelName: map[string]any{
							"$ref": fmt.Sprintf("#/definitions/%v", objectReferenceModelName),
						},
					},
					"definitions": map[string]any{
						objectReferenceModelName: objectReferenceModelDefinition,
					},
				},
				path: []string{"models", objectReferenceModelName},
			},
			wantValue: objectReferenceModelDefinition,
			wantErr:   false,
		},
		{
			name: "definitions object reference - root level",
			args: args{
				contract: DataContract{
					"models": map[string]any{
						objectReferenceModelName: map[string]any{
							"$ref": "#",
						},
					},
				},
				path: []string{"models", objectReferenceModelName},
			},
			wantValue: nil,
			wantErr:   false,
		},
		{
			name: "file object reference",
			args: args{
				contract: DataContract{
					"models": map[string]any{
						objectReferenceModelName: map[string]any{
							"$ref": fmt.Sprintf("test_resources/dataContract/getValue/models.yaml#%v", objectReferenceModelName),
						},
					},
				},
				path: []string{"models", objectReferenceModelName},
			},
			wantValue: objectReferenceModelDefinition,
			wantErr:   false,
		},
		{
			name: "file object reference - root level",
			args: args{
				contract: DataContract{
					"models": map[string]any{
						objectReferenceModelName: map[string]any{
							"$ref": "test_resources/dataContract/getValue/myModel.yaml",
						},
					},
				},
				path: []string{"models", objectReferenceModelName},
			},
			wantValue: objectReferenceModelDefinition,
			wantErr:   false,
		},
		{
			name: "remote object reference",
			args: args{
				contract: DataContract{
					"models": map[string]any{
						objectReferenceModelName: map[string]any{
							"$ref": fmt.Sprintf("%v/dataContract/getValue/models.yaml#%v", TestResourcesServer.URL, objectReferenceModelName),
						},
					},
				},
				path: []string{"models", objectReferenceModelName},
			},
			wantValue: objectReferenceModelDefinition,
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
		"dataContractSpecification": "0.9.1",
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

func TestSetValue(t *testing.T) {
	type args struct {
		contract DataContract
		path     []string
		value    any
	}
	tests := []struct {
		name string
		args args
		want any
	}{
		{
			name: "sets string value",
			args: args{
				contract: DataContract{"foo": map[string]any{"bar": "baz"}},
				path:     []string{"foo", "bar"},
				value:    "bazi",
			},
			want: "bazi",
		},
		{
			name: "sets object value",
			args: args{
				contract: DataContract{"foo": map[string]any{"bar": "baz"}},
				path:     []string{"foo", "bar"},
				value:    map[string]any{"hi": "ho"},
			},
			want: map[string]any{"hi": "ho"},
		},
		{
			name: "sets value if path does not exist yet",
			args: args{
				contract: DataContract{},
				path:     []string{"foo", "bar"},
				value:    "bazi",
			},
			want: "bazi",
		},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			SetValue(tt.args.contract, tt.args.path, tt.args.value)

			got, _ := GetValue(tt.args.contract, tt.args.path)

			if !reflect.DeepEqual(got, tt.want) {
				t.Errorf("SetDataContract() gotDataContractObject = %v, want %v", got, tt.want)
			}
		})
	}
}
