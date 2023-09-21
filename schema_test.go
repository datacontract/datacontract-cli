package main

import (
	"fmt"
	"reflect"
	"testing"
)

func TestCompareDatasets(t *testing.T) {
	type args struct {
		old Dataset
		new Dataset
	}
	tests := []struct {
		name string
		args args
		want []DatasetDifference
	}{
		{
			name: "modelWasRemoved",
			args: args{Dataset{Models: []Model{{Name: "my_table"}}}, Dataset{Models: []Model{}}},
			want: []DatasetDifference{{
				Level:       DatasetDifferenceLevelModel,
				Severity:    DatasetDifferenceSeverityBreaking,
				ModelName:   "my_table",
				Description: "model 'my_table' was removed",
			}},
		},
		{
			name: "fieldWasRemoved",
			args: args{
				Dataset{Models: []Model{{Name: "my_table", Fields: []Field{{Name: "my_column"}}}}},
				Dataset{Models: []Model{{Name: "my_table", Fields: []Field{}}}},
			},
			want: []DatasetDifference{{
				Level:       DatasetDifferenceLevelField,
				Severity:    DatasetDifferenceSeverityBreaking,
				ModelName:   "my_table",
				FieldName:   "my_column",
				Description: "field 'my_table.my_column' was removed",
			}},
		},
		{
			name: "fieldWasRemoved-subfield",
			args: args{
				Dataset{Models: []Model{{Name: "my_model", Fields: []Field{
					{Name: "my_field", Fields: []Field{{Name: "my_subfield"}}}}}}},
				Dataset{Models: []Model{{Name: "my_model", Fields: []Field{
					{Name: "my_field"}}}}},
			},
			want: []DatasetDifference{{
				Level:       DatasetDifferenceLevelField,
				Severity:    DatasetDifferenceSeverityBreaking,
				ModelName:   "my_model",
				FieldName:   "my_field.my_subfield",
				Description: "field 'my_model.my_field.my_subfield' was removed",
			}},
		},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			if got := CompareDatasets(tt.args.old, tt.args.new); !reflect.DeepEqual(got, tt.want) {
				t.Errorf("CompareDatasets() = %v, want %v", got, tt.want)
			}
		})
	}
}

func TestParseDataset(t *testing.T) {
	modelName := "email_provider_usage"
	modelType := "table"
	modelDescription := "Description of the model"

	fieldName := "email_provider"
	fieldType := "text"
	fieldDescription := "Description of the column"

	dbtSpecificationYaml := fmt.Sprintf(`version: 2
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
			name:    "unkown",
			args:    args{"unkown", []byte{}},
			wantErr: true,
		},
		{
			name: "dbt",
			args: args{"dbt", []byte(dbtSpecificationYaml)},
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
			got, err := ParseDataset(tt.args.schemaType, tt.args.specification)

			if (err != nil) != tt.wantErr {
				t.Errorf("ParseDataset() error = %v, wantErr %v", err, tt.wantErr)
				return
			}
			if got != nil && !got.equals(*tt.want) {
				t.Errorf("ParseDataset() got = %v, want %v", got, tt.want)
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
