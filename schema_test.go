package main

import (
	"fmt"
	"reflect"
	"testing"
)

func TestCompareDatasets(t *testing.T) {
	dummyString1 := "dummy1"
	dummyString2 := "dummy2"

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
			name: "modelRemoved",
			args: args{Dataset{Models: []Model{{Name: "my_table"}}}, Dataset{Models: []Model{}}},
			want: []DatasetDifference{{
				Type:        DatasetDifferenceTypeModelRemoved,
				Level:       DatasetDifferenceLevelModel,
				Severity:    DatasetDifferenceSeverityBreaking,
				ModelName:   "my_table",
				Description: "model 'my_table' was removed",
			}},
		},
		{
			name: "fieldRemoved",
			args: args{
				Dataset{Models: []Model{{Name: "my_table", Fields: []Field{{Name: "my_column"}}}}},
				Dataset{Models: []Model{{Name: "my_table", Fields: []Field{}}}},
			},
			want: []DatasetDifference{{
				Type:        DatasetDifferenceTypeFieldRemoved,
				Level:       DatasetDifferenceLevelField,
				Severity:    DatasetDifferenceSeverityBreaking,
				ModelName:   "my_table",
				FieldName:   "my_column",
				Description: "field 'my_table.my_column' was removed",
			}},
		},
		{
			name: "fieldRemoved-subfield",
			args: args{
				Dataset{Models: []Model{{Name: "my_model", Fields: []Field{
					{Name: "my_field", Fields: []Field{{Name: "my_subfield"}}}}}}},
				Dataset{Models: []Model{{Name: "my_model", Fields: []Field{
					{Name: "my_field"}}}}},
			},
			want: []DatasetDifference{{
				Type:        DatasetDifferenceTypeFieldRemoved,
				Level:       DatasetDifferenceLevelField,
				Severity:    DatasetDifferenceSeverityBreaking,
				ModelName:   "my_model",
				FieldName:   "my_field.my_subfield",
				Description: "field 'my_model.my_field.my_subfield' was removed",
			}},
		},
		{
			name: "fieldTypeChanged",
			args: args{
				Dataset{Models: []Model{{Name: "my_table", Fields: []Field{
					{Name: "my_column", Type: &dummyString1}}}}},
				Dataset{Models: []Model{{Name: "my_table", Fields: []Field{
					{Name: "my_column", Type: &dummyString2}}}}},
			},
			want: []DatasetDifference{{
				Type:        DatasetDifferenceTypeFieldTypeChanged,
				Level:       DatasetDifferenceLevelField,
				Severity:    DatasetDifferenceSeverityBreaking,
				ModelName:   "my_table",
				FieldName:   "my_column",
				Description: fmt.Sprintf("type of field 'my_table.my_column' was changed from %v to %v", dummyString1, dummyString2),
			}},
		},
		{
			name: "fieldTypeChanged-subfield",
			args: args{
				Dataset{Models: []Model{{Name: "my_model", Fields: []Field{
					{Name: "my_field", Fields: []Field{{Name: "my_subfield", Type: &dummyString1}}}}}}},
				Dataset{Models: []Model{{Name: "my_model", Fields: []Field{
					{Name: "my_field", Fields: []Field{{Name: "my_subfield", Type: &dummyString2}}}}}}},
			},
			want: []DatasetDifference{{
				Type:        DatasetDifferenceTypeFieldTypeChanged,
				Level:       DatasetDifferenceLevelField,
				Severity:    DatasetDifferenceSeverityBreaking,
				ModelName:   "my_model",
				FieldName:   "my_field.my_subfield",
				Description: fmt.Sprintf("type of field 'my_model.my_field.my_subfield' was changed from %v to %v", dummyString1, dummyString2),
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
			args: args{"dbt", []byte(fmt.Sprintf(`version: 2
models:
  - name: %v
    description: "%v"
    config:
      materialized: %v
    columns:
      - name: %v
        data_type: %v
        description: "%v"`, modelName, modelDescription, modelType, fieldName, fieldType, fieldDescription))},
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
		{
			name: "dbt-model-level-constraints",
			args: args{"dbt", []byte(fmt.Sprintf(`version: 2
models:
  - name: %v
    description: "%v"
    config:
      materialized: %v
    constraints:
      - type: not_null
        columns: [%v]
      - type: unique
        columns: [%v]
    columns:
      - name: %v
        data_type: %v
        description: "%v"`, modelName, modelDescription, modelType, fieldName, fieldName, fieldName, fieldType, fieldDescription))},
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
							Required:    true,
							Unique:      true,
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
	return fieldsAreEqual(model.Fields, other.Fields) &&
		model.Name == other.Name &&
		*model.Type == *other.Type &&
		*model.Description == *other.Description
}

func (field Field) equals(other Field) bool {
	return fieldsAreEqual(field.Fields, other.Fields) &&
		field.Name == other.Name &&
		*field.Type == *other.Type &&
		*field.Description == *other.Description &&
		field.Required == other.Required &&
		field.Unique == other.Unique &&
		fieldConstraintsAreEqual(field.AdditionalConstraints, other.AdditionalConstraints)
}

func fieldsAreEqual(fields []Field, otherFields []Field) bool {
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

func fieldConstraintsAreEqual(constraints, other []FieldConstraint) bool {
	for _, constraint := range constraints {
		if !constraint.isIn(other) {
			return false
		}
	}

	for _, constraint := range other {
		if !constraint.isIn(constraints) {
			return false
		}
	}

	return true
}

func (constraint FieldConstraint) isIn(list []FieldConstraint) bool {
	for _, fieldConstraint := range list {
		if fieldConstraint.Name == fieldConstraint.Name && fieldConstraint.Value == constraint.Value {
			return true
		}
	}
	return false
}
