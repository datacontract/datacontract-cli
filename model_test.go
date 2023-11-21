package datacontract

import (
	"fmt"
	"reflect"
	"testing"
)

func TestCompareDatasets(t *testing.T) {
	dummyString1 := "dummy1"
	dummyString2 := "dummy2"

	description1 := "contains good data"
	description2 := "contains very good data"

	modelName := "my_table"
	fieldName := "my_field"
	subFieldName := "my_subfield"
	fieldNameAndSubfieldName := fmt.Sprintf("%v.%v", fieldName, subFieldName)

	type args struct {
		old InternalDataset
		new InternalDataset
	}
	tests := []struct {
		name string
		args args
		want []ModelDifference
	}{
		{
			name: "modelRemoved",
			args: args{InternalDataset{Models: []InternalModel{{Name: modelName}}}, InternalDataset{Models: []InternalModel{}}},
			want: []ModelDifference{{
				Type:        ModelDifferenceTypeModelRemoved,
				Level:       ModelDifferenceLevelModel,
				Severity:    ModelDifferenceSeverityBreaking,
				ModelName:   &modelName,
				Description: fmt.Sprintf("model '%v' was removed", modelName),
			}},
		},
		{
			name: "fieldRemoved",
			args: args{
				InternalDataset{Models: []InternalModel{{Name: modelName, Fields: []InternalField{{Name: fieldName}}}}},
				InternalDataset{Models: []InternalModel{{Name: modelName, Fields: []InternalField{}}}},
			},
			want: []ModelDifference{{
				Type:        ModelDifferenceTypeFieldRemoved,
				Level:       ModelDifferenceLevelField,
				Severity:    ModelDifferenceSeverityBreaking,
				ModelName:   &modelName,
				FieldName:   &fieldName,
				Description: fmt.Sprintf("field '%v.%v' was removed", modelName, fieldName),
			}},
		},
		{
			name: "fieldRemoved-subfield",
			args: args{
				InternalDataset{Models: []InternalModel{{Name: modelName, Fields: []InternalField{
					{Name: fieldName, Fields: []InternalField{{Name: subFieldName}}}}}}},
				InternalDataset{Models: []InternalModel{{Name: modelName, Fields: []InternalField{
					{Name: fieldName}}}}},
			},
			want: []ModelDifference{{
				Type:        ModelDifferenceTypeFieldRemoved,
				Level:       ModelDifferenceLevelField,
				Severity:    ModelDifferenceSeverityBreaking,
				ModelName:   &modelName,
				FieldName:   &fieldNameAndSubfieldName,
				Description: fmt.Sprintf("field '%v.%v' was removed", modelName, fieldNameAndSubfieldName),
			}},
		},
		{
			name: "fieldTypeChanged",
			args: args{
				InternalDataset{Models: []InternalModel{{Name: modelName, Fields: []InternalField{
					{Name: fieldName, Type: &dummyString1}}}}},
				InternalDataset{Models: []InternalModel{{Name: modelName, Fields: []InternalField{
					{Name: fieldName, Type: &dummyString2}}}}},
			},
			want: []ModelDifference{{
				Type:        ModelDifferenceTypeFieldTypeChanged,
				Level:       ModelDifferenceLevelField,
				Severity:    ModelDifferenceSeverityBreaking,
				ModelName:   &modelName,
				FieldName:   &fieldName,
				Description: fmt.Sprintf("type of field '%v.%v' was changed from '%v' to '%v'", modelName, fieldName, dummyString1, dummyString2),
			}},
		},
		{
			name: "fieldTypeChanged-old-nil ",
			args: args{
				InternalDataset{Models: []InternalModel{{Name: modelName, Fields: []InternalField{
					{Name: fieldName}}}}},
				InternalDataset{Models: []InternalModel{{Name: modelName, Fields: []InternalField{
					{Name: fieldName, Type: &dummyString2}}}}},
			},
			want: []ModelDifference{{
				Type:        ModelDifferenceTypeFieldTypeChanged,
				Level:       ModelDifferenceLevelField,
				Severity:    ModelDifferenceSeverityBreaking,
				ModelName:   &modelName,
				FieldName:   &fieldName,
				Description: fmt.Sprintf("type of field '%v.%v' was changed from '' to '%v'", modelName, fieldName, dummyString2),
			}},
		},
		{
			name: "fieldTypeChanged-new-nil ",
			args: args{
				InternalDataset{Models: []InternalModel{{Name: modelName, Fields: []InternalField{
					{Name: fieldName, Type: &dummyString1}}}}},
				InternalDataset{Models: []InternalModel{{Name: modelName, Fields: []InternalField{
					{Name: fieldName}}}}},
			},
			want: []ModelDifference{{
				Type:        ModelDifferenceTypeFieldTypeChanged,
				Level:       ModelDifferenceLevelField,
				Severity:    ModelDifferenceSeverityBreaking,
				ModelName:   &modelName,
				FieldName:   &fieldName,
				Description: fmt.Sprintf("type of field '%v.%v' was changed from '%v' to ''", modelName, fieldName, dummyString1),
			}},
		},
		{
			name: "fieldTypeChanged-subfield",
			args: args{
				InternalDataset{Models: []InternalModel{{Name: modelName, Fields: []InternalField{
					{Name: fieldName, Fields: []InternalField{{Name: subFieldName, Type: &dummyString1}}}}}}},
				InternalDataset{Models: []InternalModel{{Name: modelName, Fields: []InternalField{
					{Name: fieldName, Fields: []InternalField{{Name: subFieldName, Type: &dummyString2}}}}}}},
			},
			want: []ModelDifference{{
				Type:        ModelDifferenceTypeFieldTypeChanged,
				Level:       ModelDifferenceLevelField,
				Severity:    ModelDifferenceSeverityBreaking,
				ModelName:   &modelName,
				FieldName:   &fieldNameAndSubfieldName,
				Description: fmt.Sprintf("type of field '%v.%v' was changed from '%v' to '%v'", modelName, fieldNameAndSubfieldName, dummyString1, dummyString2),
			}},
		},
		{
			name: "fieldRequirementRemoved",
			args: args{
				InternalDataset{Models: []InternalModel{{Name: modelName, Fields: []InternalField{
					{Name: fieldName, Required: true}}}}},
				InternalDataset{Models: []InternalModel{{Name: modelName, Fields: []InternalField{
					{Name: fieldName, Required: false}}}}},
			},
			want: []ModelDifference{{
				Type:        ModelDifferenceTypeFieldRequirementRemoved,
				Level:       ModelDifferenceLevelField,
				Severity:    ModelDifferenceSeverityBreaking,
				ModelName:   &modelName,
				FieldName:   &fieldName,
				Description: fmt.Sprintf("field requirement of '%v.%v' was removed", modelName, fieldName),
			}},
		},
		{
			name: "fieldUniquenessRemoved",
			args: args{
				InternalDataset{Models: []InternalModel{{Name: modelName, Fields: []InternalField{
					{Name: fieldName, Unique: true}}}}},
				InternalDataset{Models: []InternalModel{{Name: modelName, Fields: []InternalField{
					{Name: fieldName, Unique: false}}}}},
			},
			want: []ModelDifference{{
				Type:        ModelDifferenceTypeFieldUniquenessRemoved,
				Level:       ModelDifferenceLevelField,
				Severity:    ModelDifferenceSeverityBreaking,
				ModelName:   &modelName,
				FieldName:   &fieldName,
				Description: fmt.Sprintf("field uniqueness of '%v.%v' was removed", modelName, fieldName),
			}},
		},
		{
			name: "fieldConstraintAdded",
			args: args{
				InternalDataset{Models: []InternalModel{{Name: modelName, Fields: []InternalField{
					{Name: fieldName}}}}},
				InternalDataset{Models: []InternalModel{{Name: modelName, Fields: []InternalField{
					{Name: fieldName, AdditionalConstraints: []InternalFieldConstraint{
						{Type: "check", Expression: "id < 0"}}}}}}},
			},
			want: []ModelDifference{{
				Type:        ModelDifferenceTypeFieldAdditionalConstraintAdded,
				Level:       ModelDifferenceLevelField,
				Severity:    ModelDifferenceSeverityBreaking,
				ModelName:   &modelName,
				FieldName:   &fieldName,
				Description: fmt.Sprintf("field constraint (check: id < 0) of '%v.%v' was added", modelName, fieldName),
			}},
		},
		{
			name: "fieldConstraintRemoved",
			args: args{
				InternalDataset{Models: []InternalModel{{Name: modelName, Fields: []InternalField{
					{Name: fieldName, AdditionalConstraints: []InternalFieldConstraint{
						{Type: "custom", Expression: "special"}}}}}}},
				InternalDataset{Models: []InternalModel{{Name: modelName, Fields: []InternalField{
					{Name: fieldName}}}}},
			},
			want: []ModelDifference{{
				Type:        ModelDifferenceTypeFieldAdditionalConstraintRemoved,
				Level:       ModelDifferenceLevelField,
				Severity:    ModelDifferenceSeverityBreaking,
				ModelName:   &modelName,
				FieldName:   &fieldName,
				Description: fmt.Sprintf("field constraint (custom: special) of '%v.%v' was removed", modelName, fieldName),
			}},
		},
		{
			name: "datasetSchemaTypeChanged",
			args: args{
				InternalDataset{SchemaType: "dbt"},
				InternalDataset{SchemaType: "json-schema"},
			},
			want: []ModelDifference{{
				Type:        ModelDifferenceTypeDatasetSchemaTypeChanged,
				Level:       ModelDifferenceLevelDataset,
				Severity:    ModelDifferenceSeverityInfo,
				Description: "schema type changed from 'dbt' to 'json-schema'",
			}},
		},
		{
			name: "modelAdded",
			args: args{
				InternalDataset{},
				InternalDataset{Models: []InternalModel{{Name: modelName}}},
			},
			want: []ModelDifference{{
				Type:        ModelDifferenceTypeModelAdded,
				Level:       ModelDifferenceLevelModel,
				Severity:    ModelDifferenceSeverityInfo,
				ModelName:   &modelName,
				Description: fmt.Sprintf("model '%v' was added", modelName),
			}},
		},
		{
			name: "modelTypeChanged",
			args: args{
				InternalDataset{Models: []InternalModel{{Name: modelName, Type: &dummyString1}}},
				InternalDataset{Models: []InternalModel{{Name: modelName, Type: &dummyString2}}},
			},
			want: []ModelDifference{{
				Type:        ModelDifferenceTypeModelTypeChanged,
				Level:       ModelDifferenceLevelModel,
				Severity:    ModelDifferenceSeverityInfo,
				ModelName:   &modelName,
				Description: fmt.Sprintf("type of model '%v' was changed from '%v' to '%v'", modelName, dummyString1, dummyString2),
			}},
		},
		{
			name: "fieldAdded",
			args: args{
				InternalDataset{Models: []InternalModel{{Name: modelName, Fields: []InternalField{}}}},
				InternalDataset{Models: []InternalModel{{Name: modelName, Fields: []InternalField{{Name: fieldName}}}}},
			},
			want: []ModelDifference{{
				Type:        ModelDifferenceTypeFieldAdded,
				Level:       ModelDifferenceLevelField,
				Severity:    ModelDifferenceSeverityInfo,
				ModelName:   &modelName,
				FieldName:   &fieldName,
				Description: fmt.Sprintf("field '%v.%v' was added", modelName, fieldName),
			}},
		},
		{
			name: "fieldRequirementAdded",
			args: args{
				InternalDataset{Models: []InternalModel{{Name: modelName, Fields: []InternalField{
					{Name: fieldName, Required: false}}}}},
				InternalDataset{Models: []InternalModel{{Name: modelName, Fields: []InternalField{
					{Name: fieldName, Required: true}}}}},
			},
			want: []ModelDifference{{
				Type:        ModelDifferenceTypeFieldRequirementAdded,
				Level:       ModelDifferenceLevelField,
				Severity:    ModelDifferenceSeverityInfo,
				ModelName:   &modelName,
				FieldName:   &fieldName,
				Description: fmt.Sprintf("field requirement of '%v.%v' was added", modelName, fieldName),
			}},
		},
		{
			name: "fieldUniquenessAdded",
			args: args{
				InternalDataset{Models: []InternalModel{{Name: modelName, Fields: []InternalField{
					{Name: fieldName, Unique: false}}}}},
				InternalDataset{Models: []InternalModel{{Name: modelName, Fields: []InternalField{
					{Name: fieldName, Unique: true}}}}},
			},
			want: []ModelDifference{{
				Type:        ModelDifferenceTypeFieldUniquenessAdded,
				Level:       ModelDifferenceLevelField,
				Severity:    ModelDifferenceSeverityInfo,
				ModelName:   &modelName,
				FieldName:   &fieldName,
				Description: fmt.Sprintf("field uniqueness of '%v.%v' was added", modelName, fieldName),
			}},
		},
		{
			name: "fieldDescriptionChanged",
			args: args{
				InternalDataset{Models: []InternalModel{{Name: modelName, Fields: []InternalField{
					{Name: fieldName, Description: &description1}}}}},
				InternalDataset{Models: []InternalModel{{Name: modelName, Fields: []InternalField{
					{Name: fieldName, Description: &description2}}}}},
			},
			want: []ModelDifference{{
				Type:        ModelDifferenceTypeFieldDescriptionChanged,
				Level:       ModelDifferenceLevelField,
				Severity:    ModelDifferenceSeverityInfo,
				ModelName:   &modelName,
				FieldName:   &fieldName,
				Description: fmt.Sprintf("description of field '%v.%v' has changed from '%v' to '%v'", modelName, fieldName, description1, description2),
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
