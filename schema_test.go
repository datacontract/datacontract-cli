package main

import (
	"fmt"
	"testing"
)

var modelName = "email_provider_usage"
var modelType = "table"
var modelDescription = "Description of the model"

var fieldName = "email_provider"
var fieldType = "text"
var fieldDescription = "Description of the column"

var dbtSpecificationYaml = fmt.Sprintf(`version: 2
models:
  - name: %v
    description: "%v"
    config:
      materialized: %v
    columns:
      - name: %v
        data_type: %v
        description: "%v"`,
	modelName, modelDescription, modelType, fieldName, fieldType, fieldDescription)

func Test_parseDataset(t *testing.T) {
	type args struct {
		schemaType    string
		specification []byte
	}

	tests := []struct {
		name    string
		args    args
		want    *Dataset
		wantErr bool
	}{
		{
			name: "unkown", args: args{"unkown", []byte{}},
			wantErr: true,
		},
		{
			name: "dbt", args: args{"dbt", []byte(dbtSpecificationYaml)},
			want: &Dataset{Models: []Model{
				{
					Name:        modelName,
					Type:        &modelType,
					Description: &modelDescription,
					Fields: []Field{
						{
							Name:        fieldName,
							Type:        &fieldType,
							Description: &fieldDescription,
						},
					},
				},
			}},
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got, err := parseDataset(tt.args.schemaType, tt.args.specification)

			if (err != nil) != tt.wantErr {
				t.Errorf("parseDataset() error = %v, wantErr %v", err, tt.wantErr)
				return
			}
			if got != nil && !got.equals(*tt.want) {
				t.Errorf("parseDataset() got = %v, want %v", got, tt.want)
			}
		})
	}
}

func (dataset Dataset) equals(other Dataset) bool {
	if len(dataset.Models) != len(other.Models) {
		return false
	}

	for i, model := range dataset.Models {
		if !model.equals(other.Models[i]) {
			return false
		}
	}

	return true
}

func (model Model) equals(other Model) bool {
	return equal(model.Fields, other.Fields) &&
		model.Name == other.Name &&
		*model.Type == *other.Type &&
		*model.Description == *other.Description
}

func (field Field) equals(other Field) bool {
	return equal(field.Fields, other.Fields) &&
		field.Name == other.Name &&
		*field.Type == *other.Type &&
		*field.Description == *other.Description
}

func equal(fields []Field, otherFields []Field) bool {
	if len(fields) != len(otherFields) {
		return false
	}
	for i, field := range fields {
		if !field.equals(otherFields[i]) {
			return false
		}
	}

	return true
}
