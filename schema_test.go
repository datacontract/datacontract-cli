package cli

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
			args: args{Dataset{Models: []Model{{Name: modelName}}}, Dataset{Models: []Model{}}},
			want: []DatasetDifference{{
				Type:        DatasetDifferenceTypeModelRemoved,
				Level:       DatasetDifferenceLevelModel,
				Severity:    DatasetDifferenceSeverityBreaking,
				ModelName:   &modelName,
				Description: fmt.Sprintf("model '%v' was removed", modelName),
			}},
		},
		{
			name: "fieldRemoved",
			args: args{
				Dataset{Models: []Model{{Name: modelName, Fields: []Field{{Name: fieldName}}}}},
				Dataset{Models: []Model{{Name: modelName, Fields: []Field{}}}},
			},
			want: []DatasetDifference{{
				Type:        DatasetDifferenceTypeFieldRemoved,
				Level:       DatasetDifferenceLevelField,
				Severity:    DatasetDifferenceSeverityBreaking,
				ModelName:   &modelName,
				FieldName:   &fieldName,
				Description: fmt.Sprintf("field '%v.%v' was removed", modelName, fieldName),
			}},
		},
		{
			name: "fieldRemoved-subfield",
			args: args{
				Dataset{Models: []Model{{Name: modelName, Fields: []Field{
					{Name: fieldName, Fields: []Field{{Name: subFieldName}}}}}}},
				Dataset{Models: []Model{{Name: modelName, Fields: []Field{
					{Name: fieldName}}}}},
			},
			want: []DatasetDifference{{
				Type:        DatasetDifferenceTypeFieldRemoved,
				Level:       DatasetDifferenceLevelField,
				Severity:    DatasetDifferenceSeverityBreaking,
				ModelName:   &modelName,
				FieldName:   &fieldNameAndSubfieldName,
				Description: fmt.Sprintf("field '%v.%v' was removed", modelName, fieldNameAndSubfieldName),
			}},
		},
		{
			name: "fieldTypeChanged",
			args: args{
				Dataset{Models: []Model{{Name: modelName, Fields: []Field{
					{Name: fieldName, Type: &dummyString1}}}}},
				Dataset{Models: []Model{{Name: modelName, Fields: []Field{
					{Name: fieldName, Type: &dummyString2}}}}},
			},
			want: []DatasetDifference{{
				Type:        DatasetDifferenceTypeFieldTypeChanged,
				Level:       DatasetDifferenceLevelField,
				Severity:    DatasetDifferenceSeverityBreaking,
				ModelName:   &modelName,
				FieldName:   &fieldName,
				Description: fmt.Sprintf("type of field '%v.%v' was changed from '%v' to '%v'", modelName, fieldName, dummyString1, dummyString2),
			}},
		},
		{
			name: "fieldTypeChanged-old-nil ",
			args: args{
				Dataset{Models: []Model{{Name: modelName, Fields: []Field{
					{Name: fieldName}}}}},
				Dataset{Models: []Model{{Name: modelName, Fields: []Field{
					{Name: fieldName, Type: &dummyString2}}}}},
			},
			want: []DatasetDifference{{
				Type:        DatasetDifferenceTypeFieldTypeChanged,
				Level:       DatasetDifferenceLevelField,
				Severity:    DatasetDifferenceSeverityBreaking,
				ModelName:   &modelName,
				FieldName:   &fieldName,
				Description: fmt.Sprintf("type of field '%v.%v' was changed from '' to '%v'", modelName, fieldName, dummyString2),
			}},
		},
		{
			name: "fieldTypeChanged-new-nil ",
			args: args{
				Dataset{Models: []Model{{Name: modelName, Fields: []Field{
					{Name: fieldName, Type: &dummyString1}}}}},
				Dataset{Models: []Model{{Name: modelName, Fields: []Field{
					{Name: fieldName}}}}},
			},
			want: []DatasetDifference{{
				Type:        DatasetDifferenceTypeFieldTypeChanged,
				Level:       DatasetDifferenceLevelField,
				Severity:    DatasetDifferenceSeverityBreaking,
				ModelName:   &modelName,
				FieldName:   &fieldName,
				Description: fmt.Sprintf("type of field '%v.%v' was changed from '%v' to ''", modelName, fieldName, dummyString1),
			}},
		},
		{
			name: "fieldTypeChanged-subfield",
			args: args{
				Dataset{Models: []Model{{Name: modelName, Fields: []Field{
					{Name: fieldName, Fields: []Field{{Name: subFieldName, Type: &dummyString1}}}}}}},
				Dataset{Models: []Model{{Name: modelName, Fields: []Field{
					{Name: fieldName, Fields: []Field{{Name: subFieldName, Type: &dummyString2}}}}}}},
			},
			want: []DatasetDifference{{
				Type:        DatasetDifferenceTypeFieldTypeChanged,
				Level:       DatasetDifferenceLevelField,
				Severity:    DatasetDifferenceSeverityBreaking,
				ModelName:   &modelName,
				FieldName:   &fieldNameAndSubfieldName,
				Description: fmt.Sprintf("type of field '%v.%v' was changed from '%v' to '%v'", modelName, fieldNameAndSubfieldName, dummyString1, dummyString2),
			}},
		},
		{
			name: "fieldRequirementRemoved",
			args: args{
				Dataset{Models: []Model{{Name: modelName, Fields: []Field{
					{Name: fieldName, Required: true}}}}},
				Dataset{Models: []Model{{Name: modelName, Fields: []Field{
					{Name: fieldName, Required: false}}}}},
			},
			want: []DatasetDifference{{
				Type:        DatasetDifferenceTypeFieldRequirementRemoved,
				Level:       DatasetDifferenceLevelField,
				Severity:    DatasetDifferenceSeverityBreaking,
				ModelName:   &modelName,
				FieldName:   &fieldName,
				Description: fmt.Sprintf("field requirement of '%v.%v' was removed", modelName, fieldName),
			}},
		},
		{
			name: "fieldUniquenessRemoved",
			args: args{
				Dataset{Models: []Model{{Name: modelName, Fields: []Field{
					{Name: fieldName, Unique: true}}}}},
				Dataset{Models: []Model{{Name: modelName, Fields: []Field{
					{Name: fieldName, Unique: false}}}}},
			},
			want: []DatasetDifference{{
				Type:        DatasetDifferenceTypeFieldUniquenessRemoved,
				Level:       DatasetDifferenceLevelField,
				Severity:    DatasetDifferenceSeverityBreaking,
				ModelName:   &modelName,
				FieldName:   &fieldName,
				Description: fmt.Sprintf("field uniqueness of '%v.%v' was removed", modelName, fieldName),
			}},
		},
		{
			name: "fieldConstraintAdded",
			args: args{
				Dataset{Models: []Model{{Name: modelName, Fields: []Field{
					{Name: fieldName}}}}},
				Dataset{Models: []Model{{Name: modelName, Fields: []Field{
					{Name: fieldName, AdditionalConstraints: []FieldConstraint{
						{Type: "check", Expression: "id < 0"}}}}}}},
			},
			want: []DatasetDifference{{
				Type:        DatasetDifferenceTypeFieldAdditionalConstraintAdded,
				Level:       DatasetDifferenceLevelField,
				Severity:    DatasetDifferenceSeverityBreaking,
				ModelName:   &modelName,
				FieldName:   &fieldName,
				Description: fmt.Sprintf("field constraint (check: id < 0) of '%v.%v' was added", modelName, fieldName),
			}},
		},
		{
			name: "fieldConstraintRemoved",
			args: args{
				Dataset{Models: []Model{{Name: modelName, Fields: []Field{
					{Name: fieldName, AdditionalConstraints: []FieldConstraint{
						{Type: "custom", Expression: "special"}}}}}}},
				Dataset{Models: []Model{{Name: modelName, Fields: []Field{
					{Name: fieldName}}}}},
			},
			want: []DatasetDifference{{
				Type:        DatasetDifferenceTypeFieldAdditionalConstraintRemoved,
				Level:       DatasetDifferenceLevelField,
				Severity:    DatasetDifferenceSeverityBreaking,
				ModelName:   &modelName,
				FieldName:   &fieldName,
				Description: fmt.Sprintf("field constraint (custom: special) of '%v.%v' was removed", modelName, fieldName),
			}},
		},
		{
			name: "datasetSchemaTypeChanged",
			args: args{
				Dataset{SchemaType: "dbt"},
				Dataset{SchemaType: "json-schema"},
			},
			want: []DatasetDifference{{
				Type:        DatasetDifferenceTypeDatasetSchemaTypeChanged,
				Level:       DatasetDifferenceLevelDataset,
				Severity:    DatasetDifferenceSeverityInfo,
				Description: "schema type changed from 'dbt' to 'json-schema'",
			}},
		},
		{
			name: "modelAdded",
			args: args{
				Dataset{},
				Dataset{Models: []Model{{Name: modelName}}},
			},
			want: []DatasetDifference{{
				Type:        DatasetDifferenceTypeModelAdded,
				Level:       DatasetDifferenceLevelModel,
				Severity:    DatasetDifferenceSeverityInfo,
				ModelName:   &modelName,
				Description: fmt.Sprintf("model '%v' was added", modelName),
			}},
		},
		{
			name: "modelTypeChanged",
			args: args{
				Dataset{Models: []Model{{Name: modelName, Type: &dummyString1}}},
				Dataset{Models: []Model{{Name: modelName, Type: &dummyString2}}},
			},
			want: []DatasetDifference{{
				Type:        DatasetDifferenceTypeModelTypeChanged,
				Level:       DatasetDifferenceLevelModel,
				Severity:    DatasetDifferenceSeverityInfo,
				ModelName:   &modelName,
				Description: fmt.Sprintf("type of model '%v' was changed from '%v' to '%v'", modelName, dummyString1, dummyString2),
			}},
		},
		{
			name: "fieldAdded",
			args: args{
				Dataset{Models: []Model{{Name: modelName, Fields: []Field{}}}},
				Dataset{Models: []Model{{Name: modelName, Fields: []Field{{Name: fieldName}}}}},
			},
			want: []DatasetDifference{{
				Type:        DatasetDifferenceTypeFieldAdded,
				Level:       DatasetDifferenceLevelField,
				Severity:    DatasetDifferenceSeverityInfo,
				ModelName:   &modelName,
				FieldName:   &fieldName,
				Description: fmt.Sprintf("field '%v.%v' was added", modelName, fieldName),
			}},
		},
		{
			name: "fieldRequirementAdded",
			args: args{
				Dataset{Models: []Model{{Name: modelName, Fields: []Field{
					{Name: fieldName, Required: false}}}}},
				Dataset{Models: []Model{{Name: modelName, Fields: []Field{
					{Name: fieldName, Required: true}}}}},
			},
			want: []DatasetDifference{{
				Type:        DatasetDifferenceTypeFieldRequirementAdded,
				Level:       DatasetDifferenceLevelField,
				Severity:    DatasetDifferenceSeverityInfo,
				ModelName:   &modelName,
				FieldName:   &fieldName,
				Description: fmt.Sprintf("field requirement of '%v.%v' was added", modelName, fieldName),
			}},
		},
		{
			name: "fieldUniquenessAdded",
			args: args{
				Dataset{Models: []Model{{Name: modelName, Fields: []Field{
					{Name: fieldName, Unique: false}}}}},
				Dataset{Models: []Model{{Name: modelName, Fields: []Field{
					{Name: fieldName, Unique: true}}}}},
			},
			want: []DatasetDifference{{
				Type:        DatasetDifferenceTypeFieldUniquenessAdded,
				Level:       DatasetDifferenceLevelField,
				Severity:    DatasetDifferenceSeverityInfo,
				ModelName:   &modelName,
				FieldName:   &fieldName,
				Description: fmt.Sprintf("field uniqueness of '%v.%v' was added", modelName, fieldName),
			}},
		},
		{
			name: "fieldDescriptionChanged",
			args: args{
				Dataset{Models: []Model{{Name: modelName, Fields: []Field{
					{Name: fieldName, Description: &description1}}}}},
				Dataset{Models: []Model{{Name: modelName, Fields: []Field{
					{Name: fieldName, Description: &description2}}}}},
			},
			want: []DatasetDifference{{
				Type:        DatasetDifferenceTypeFieldDescriptionChanged,
				Level:       DatasetDifferenceLevelField,
				Severity:    DatasetDifferenceSeverityInfo,
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

func TestExtractSchemaSpecification(t *testing.T) {
	specificationString := `version: 2
models:
  - name: my_table
    description: "contains data"
    config:
      materialized: table
    columns:
      - name: my_column
        data_type: text
        description: "contains values"`

	specificationMap := map[string]interface{}{
		"version": 2,
		"models": []map[string]interface{}{
			{
				"name":        "my_table",
				"description": "contains data",
				"config": map[string]interface{}{
					"materialized": "table",
				},
				"columns": []map[string]interface{}{
					{
						"name":        "my_column",
						"data_type":   "text",
						"description": "contains values",
					},
				},
			},
		},
	}

	type args struct {
		contract DataContract
	}
	tests := []struct {
		name              string
		args              args
		wantSchemaType    string
		wantSpecification interface{}
		wantErr           bool
	}{
		{
			name: "map",
			args: args{contract: DataContract{"schema": map[string]interface{}{
				"type":          "dbt",
				"specification": specificationMap,
			}}},
			wantSchemaType:    "dbt",
			wantSpecification: specificationMap,
			wantErr:           false,
		},
		{
			name: "string",
			args: args{contract: DataContract{"schema": map[string]interface{}{
				"type":          "dbt",
				"specification": specificationString,
			}}},
			wantSchemaType:    "dbt",
			wantSpecification: specificationString,
			wantErr:           false,
		},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			gotSchemaType, gotSpecification, err := extractSchemaSpecification(tt.args.contract, []string{"schema", "type"}, []string{"schema", "specification"})
			if (err != nil) != tt.wantErr {
				t.Errorf("extractSchemaSpecification() error = %v, wantErr %v", err, tt.wantErr)
				return
			}
			if gotSchemaType != tt.wantSchemaType {
				t.Errorf("extractSchemaSpecification() got schemaType = %v, want %v", gotSchemaType, tt.wantSchemaType)
			}

			var equal bool
			if _, ok := gotSpecification.(map[string]interface{}); ok {
				equal = reflect.DeepEqual(gotSpecification, tt.wantSpecification)
			} else {
				equal = gotSpecification == tt.wantSpecification
			}

			if !equal {
				t.Errorf("extractSchemaSpecification() got specification = %v, want %v", gotSpecification, tt.wantSpecification)
			}
		})
	}
}

func TestParseDataset(t *testing.T) {
	modelName := "email_provider_usage"
	modelType := "table"
	modelDescription := "Description of the model"

	otherModelName := "other_model_name"
	otherModelType := "other_model_type"
	otherModelDescription := "other_model_description"

	fieldName := "email_provider"
	fieldType := "text"
	fieldDescription := "Description of the column"

	otherFieldName := "other"
	otherFieldType := "timestamp"
	otherFieldDescription := "other field"

	type args struct {
		schemaType    string
		specification []byte
	}

	tests := []struct {
		name string
		args args
		want Dataset
	}{
		{
			name: "unkown",
			args: args{"unkown", []byte{}},
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
			want: Dataset{Models: []Model{
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
      - type: check
        expression: "id > 0"
        columns: [%v]
    columns:
      - name: %v
        data_type: %v
        description: "%v"`, modelName, modelDescription, modelType, fieldName, fieldName, fieldName, fieldName, fieldType, fieldDescription))},
			want: Dataset{Models: []Model{
				{
					Name:        modelName,
					Type:        &modelType,
					Description: &modelDescription,
					Fields: []Field{
						{
							Name:                  fieldName,
							Type:                  &fieldType,
							Description:           &fieldDescription,
							Required:              true,
							Unique:                true,
							AdditionalConstraints: []FieldConstraint{{Type: "check", Expression: "id > 0"}},
						},
					},
				},
			}},
		},
		{
			name: "dbt-column-level-constraints",
			args: args{"dbt", []byte(fmt.Sprintf(`version: 2
models:
  - name: %v
    description: "%v"
    config:
      materialized: %v
    columns:
      - name: %v
        data_type: %v
        description: "%v"
        constraints:
          - type: not_null
          - type: unique
          - type: check
            expression: "id > 0"
`, modelName, modelDescription, modelType, fieldName, fieldType, fieldDescription))},
			want: Dataset{Models: []Model{
				{
					Name:        modelName,
					Type:        &modelType,
					Description: &modelDescription,
					Fields: []Field{
						{
							Name:                  fieldName,
							Type:                  &fieldType,
							Description:           &fieldDescription,
							Required:              true,
							Unique:                true,
							AdditionalConstraints: []FieldConstraint{{Type: "check", Expression: "id > 0"}},
						},
					},
				},
			}},
		},
		{
			name: "dbt-two-models",
			args: args{"dbt", []byte(fmt.Sprintf(`version: 2
models:
  - name: %v
    description: "%v"
    config:
      materialized: %v  
  - name: %v
    description: "%v"
    config:
      materialized: %v
`, modelName, modelDescription, modelType, otherModelName, otherModelDescription, otherModelType))},
			want: Dataset{Models: []Model{
				{
					Name:        modelName,
					Type:        &modelType,
					Description: &modelDescription,
					Fields:      []Field{},
				},
				{
					Name:        otherModelName,
					Type:        &otherModelType,
					Description: &otherModelDescription,
					Fields:      []Field{},
				},
			}},
		},
		{
			name: "dbt-two-columns",
			args: args{"dbt", []byte(fmt.Sprintf(`version: 2
models:
  - name: %v
    description: "%v"
    config:
      materialized: %v
    columns:
      - name: %v
        data_type: %v
        description: %v
      - name: %v
        data_type: %v
        description: %v
`, modelName, modelDescription, modelType, fieldName, fieldType, fieldDescription, otherFieldName, otherFieldType, otherFieldDescription))},
			want: Dataset{Models: []Model{
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
						{
							Name:        otherFieldName,
							Type:        &otherFieldType,
							Description: &otherFieldDescription,
						},
					},
				},
			}},
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got := parseDataset(tt.args.schemaType, tt.args.specification)

			if !got.equals(tt.want) {
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

func TestPrintSchema(t *testing.T) {
	type args struct {
		dataContractLocation string
		pathToSpecification  []string
	}
	tests := []LogOutputTest[args]{
		{
			name: "print",
			args: args{
				dataContractLocation: "test_resources/schema/datacontract.yaml",
				pathToSpecification:  []string{"schema", "specification"},
			},
			wantErr: false,
			wantOutput: `version: 2
models:
  - name: my_table
    description: "contains data"
    config:
      materialized: table
    columns:
      - name: my_column
        data_type: text
        description: "contains values"

`,
		},
	}
	for _, tt := range tests {
		RunLogOutputTest(t, tt, "PrintSchema", func() error {
			return PrintSchema(tt.args.dataContractLocation, tt.args.pathToSpecification)
		})
	}
}
