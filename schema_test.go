package datacontract

import (
	"fmt"
	"reflect"
	"testing"
)

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

	specificationMap := map[string]any{
		"version": 2,
		"models": []map[string]any{
			{
				"name":        "my_table",
				"description": "contains data",
				"config": map[string]any{
					"materialized": "table",
				},
				"columns": []map[string]any{
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
		wantSpecification any
		wantErr           bool
	}{
		{
			name: "map",
			args: args{contract: DataContract{"schema": map[string]any{
				"type":          "dbt",
				"specification": specificationMap,
			}}},
			wantSchemaType:    "dbt",
			wantSpecification: specificationMap,
			wantErr:           false,
		},
		{
			name: "string",
			args: args{contract: DataContract{"schema": map[string]any{
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
			if _, ok := gotSpecification.(map[string]any); ok {
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
		want InternalModelSpecification
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
			want: InternalModelSpecification{Models: []InternalModel{
				{
					Name:        modelName,
					Type:        &modelType,
					Description: &modelDescription,
					Fields: []InternalField{
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
			want: InternalModelSpecification{Models: []InternalModel{
				{
					Name:        modelName,
					Type:        &modelType,
					Description: &modelDescription,
					Fields: []InternalField{
						{
							Name:                  fieldName,
							Type:                  &fieldType,
							Description:           &fieldDescription,
							Required:              true,
							Unique:                true,
							AdditionalConstraints: []InternalFieldConstraint{{Type: "check", Expression: "id > 0"}},
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
			want: InternalModelSpecification{Models: []InternalModel{
				{
					Name:        modelName,
					Type:        &modelType,
					Description: &modelDescription,
					Fields: []InternalField{
						{
							Name:                  fieldName,
							Type:                  &fieldType,
							Description:           &fieldDescription,
							Required:              true,
							Unique:                true,
							AdditionalConstraints: []InternalFieldConstraint{{Type: "check", Expression: "id > 0"}},
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
			want: InternalModelSpecification{Models: []InternalModel{
				{
					Name:        modelName,
					Type:        &modelType,
					Description: &modelDescription,
					Fields:      []InternalField{},
				},
				{
					Name:        otherModelName,
					Type:        &otherModelType,
					Description: &otherModelDescription,
					Fields:      []InternalField{},
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
			want: InternalModelSpecification{Models: []InternalModel{
				{
					Name:        modelName,
					Type:        &modelType,
					Description: &modelDescription,
					Fields: []InternalField{
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

func (dataset InternalModelSpecification) equals(other InternalModelSpecification) bool {
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

func (model InternalModel) equals(other InternalModel) bool {
	return fieldsAreEqual(model.Fields, other.Fields) &&
		model.Name == other.Name &&
		*model.Type == *other.Type &&
		*model.Description == *other.Description
}

func (field InternalField) equals(other InternalField) bool {
	return fieldsAreEqual(field.Fields, other.Fields) &&
		field.Name == other.Name &&
		*field.Type == *other.Type &&
		*field.Description == *other.Description &&
		field.Required == other.Required &&
		field.Unique == other.Unique &&
		fieldConstraintsAreEqual(field.AdditionalConstraints, other.AdditionalConstraints)
}

func fieldsAreEqual(fields []InternalField, otherFields []InternalField) bool {
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

func fieldConstraintsAreEqual(constraints, other []InternalFieldConstraint) bool {
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
