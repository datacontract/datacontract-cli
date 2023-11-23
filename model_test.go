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
		old InternalModelSpecification
		new InternalModelSpecification
	}
	tests := []struct {
		name string
		args args
		want []ModelDifference
	}{
		{
			name: "modelRemoved",
			args: args{InternalModelSpecification{Models: []InternalModel{{Name: modelName}}}, InternalModelSpecification{Models: []InternalModel{}}},
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
				InternalModelSpecification{Models: []InternalModel{{Name: modelName, Fields: []InternalField{{Name: fieldName}}}}},
				InternalModelSpecification{Models: []InternalModel{{Name: modelName, Fields: []InternalField{}}}},
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
				InternalModelSpecification{Models: []InternalModel{{Name: modelName, Fields: []InternalField{
					{Name: fieldName, Fields: []InternalField{{Name: subFieldName}}}}}}},
				InternalModelSpecification{Models: []InternalModel{{Name: modelName, Fields: []InternalField{
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
				InternalModelSpecification{Models: []InternalModel{{Name: modelName, Fields: []InternalField{
					{Name: fieldName, Type: &dummyString1}}}}},
				InternalModelSpecification{Models: []InternalModel{{Name: modelName, Fields: []InternalField{
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
				InternalModelSpecification{Models: []InternalModel{{Name: modelName, Fields: []InternalField{
					{Name: fieldName}}}}},
				InternalModelSpecification{Models: []InternalModel{{Name: modelName, Fields: []InternalField{
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
				InternalModelSpecification{Models: []InternalModel{{Name: modelName, Fields: []InternalField{
					{Name: fieldName, Type: &dummyString1}}}}},
				InternalModelSpecification{Models: []InternalModel{{Name: modelName, Fields: []InternalField{
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
				InternalModelSpecification{Models: []InternalModel{{Name: modelName, Fields: []InternalField{
					{Name: fieldName, Fields: []InternalField{{Name: subFieldName, Type: &dummyString1}}}}}}},
				InternalModelSpecification{Models: []InternalModel{{Name: modelName, Fields: []InternalField{
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
				InternalModelSpecification{Models: []InternalModel{{Name: modelName, Fields: []InternalField{
					{Name: fieldName, Required: true}}}}},
				InternalModelSpecification{Models: []InternalModel{{Name: modelName, Fields: []InternalField{
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
				InternalModelSpecification{Models: []InternalModel{{Name: modelName, Fields: []InternalField{
					{Name: fieldName, Unique: true}}}}},
				InternalModelSpecification{Models: []InternalModel{{Name: modelName, Fields: []InternalField{
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
				InternalModelSpecification{Models: []InternalModel{{Name: modelName, Fields: []InternalField{
					{Name: fieldName}}}}},
				InternalModelSpecification{Models: []InternalModel{{Name: modelName, Fields: []InternalField{
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
				InternalModelSpecification{Models: []InternalModel{{Name: modelName, Fields: []InternalField{
					{Name: fieldName, AdditionalConstraints: []InternalFieldConstraint{
						{Type: "custom", Expression: "special"}}}}}}},
				InternalModelSpecification{Models: []InternalModel{{Name: modelName, Fields: []InternalField{
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
				InternalModelSpecification{Type: "dbt"},
				InternalModelSpecification{Type: "json-schema"},
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
				InternalModelSpecification{},
				InternalModelSpecification{Models: []InternalModel{{Name: modelName}}},
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
				InternalModelSpecification{Models: []InternalModel{{Name: modelName, Type: &dummyString1}}},
				InternalModelSpecification{Models: []InternalModel{{Name: modelName, Type: &dummyString2}}},
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
				InternalModelSpecification{Models: []InternalModel{{Name: modelName, Fields: []InternalField{}}}},
				InternalModelSpecification{Models: []InternalModel{{Name: modelName, Fields: []InternalField{{Name: fieldName}}}}},
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
				InternalModelSpecification{Models: []InternalModel{{Name: modelName, Fields: []InternalField{
					{Name: fieldName, Required: false}}}}},
				InternalModelSpecification{Models: []InternalModel{{Name: modelName, Fields: []InternalField{
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
				InternalModelSpecification{Models: []InternalModel{{Name: modelName, Fields: []InternalField{
					{Name: fieldName, Unique: false}}}}},
				InternalModelSpecification{Models: []InternalModel{{Name: modelName, Fields: []InternalField{
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
				InternalModelSpecification{Models: []InternalModel{{Name: modelName, Fields: []InternalField{
					{Name: fieldName, Description: &description1}}}}},
				InternalModelSpecification{Models: []InternalModel{{Name: modelName, Fields: []InternalField{
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
			if got := CompareModelSpecifications(tt.args.old, tt.args.new); !reflect.DeepEqual(got, tt.want) {
				t.Errorf("CompareModelSpecifications() = %v, want %v", got, tt.want)
			}
		})
	}
}

func TestGetSpecModelSpecification(t *testing.T) {
	modelName := "myModel"
	modelDescription := "my model description"
	modelType := "table"
	fieldName := "my_id"
	fieldType := "int"
	fieldDescription := "my field description"

	fieldDefinition := map[string]any{
		"type":        fieldType,
		"description": fieldDescription,
	}
	modelDefinition := map[string]any{
		"description": modelDescription,
		"type":        modelType,
		"fields": map[string]any{
			fieldName: fieldDefinition,
		},
	}

	expected := InternalModelSpecification{
		Type: "data-contract-specification",
		Models: []InternalModel{
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
		},
	}

	type args struct {
		contract     DataContract
		pathToModels []string
	}
	tests := []struct {
		name    string
		args    args
		want    *InternalModelSpecification
		wantErr bool
	}{
		{
			name: "simple model",
			args: args{
				contract: DataContract{
					"models": map[string]any{
						modelName: modelDefinition,
					},
				},
				pathToModels: []string{"models"},
			},
			want:    &expected,
			wantErr: false,
		},
		{
			name: "with definitions reference on model",
			args: args{
				contract: DataContract{
					"models": map[string]any{
						modelName: map[string]any{
							"$ref": fmt.Sprintf("#/definitions/%v", modelName),
						},
					},
					"definitions": map[string]any{
						modelName: modelDefinition,
					},
				},
				pathToModels: []string{"models"},
			},
			want:    &expected,
			wantErr: false,
		},
		{
			name: "with definitions reference on model - reference in referenced object",
			args: args{
				contract: DataContract{
					"models": map[string]any{
						modelName: map[string]any{
							"$ref": fmt.Sprintf("#/definitions/%v_1", modelName),
						},
					},
					"definitions": map[string]any{
						fmt.Sprintf("%v_1", modelName): map[string]any{
							"$ref": fmt.Sprintf("#/definitions/%v", modelName),
						},
						modelName: map[string]any{
							"description": modelDescription,
							"type":        modelType,
							"fields": map[string]any{
								fieldName: map[string]any{
									"$ref": fmt.Sprintf("#/definitions/%v", fieldName),
								},
							},
						},
						fieldName: fieldDefinition,
					},
				},
				pathToModels: []string{"models"},
			},
			want:    &expected,
			wantErr: false,
		},
		{
			name: "with definitions reference on field",
			args: args{
				contract: DataContract{
					"models": map[string]any{
						modelName: map[string]any{
							"description": modelDescription,
							"type":        modelType,
							"fields": map[string]any{
								fieldName: map[string]any{
									"$ref": fmt.Sprintf("#/definitions/%v", fieldName),
								},
							},
						},
					},
					"definitions": map[string]any{
						fieldName: fieldDefinition,
					},
				},
				pathToModels: []string{"models"},
			},
			want:    &expected,
			wantErr: false,
		},
		{
			name: "with local file reference on model",
			args: args{
				contract: DataContract{
					"models": map[string]any{
						modelName: map[string]any{
							"$ref": fmt.Sprintf("test_resources/model/model_definition.yaml#%v", modelName),
						},
					},
				},
				pathToModels: []string{"models"},
			},
			want:    &expected,
			wantErr: false,
		},
		{
			name: "with local file reference on field",
			args: args{
				contract: DataContract{
					"models": map[string]any{
						modelName: map[string]any{
							"description": modelDescription,
							"type":        modelType,
							"fields": map[string]any{
								fieldName: map[string]any{
									"$ref": fmt.Sprintf("test_resources/model/field_definition.yaml#%v", fieldName),
								},
							},
						},
					},
				},
				pathToModels: []string{"models"},
			},
			want:    &expected,
			wantErr: false,
		},
		{
			name: "with remote reference on model",
			args: args{
				contract: DataContract{
					"models": map[string]any{
						modelName: map[string]any{
							"$ref": fmt.Sprintf("%v/model/model_definition.yaml#%v", TestResourcesServer.URL, modelName),
						},
					},
				},
				pathToModels: []string{"models"},
			},
			want:    &expected,
			wantErr: false,
		},
		{
			name: "with remote reference on field",
			args: args{
				contract: DataContract{
					"models": map[string]any{
						modelName: map[string]any{
							"description": modelDescription,
							"type":        modelType,
							"fields": map[string]any{
								fieldName: map[string]any{
									"$ref": fmt.Sprintf("%v/model/field_definition.yaml#%v", TestResourcesServer.URL, fieldName),
								},
							},
						},
					},
				},
				pathToModels: []string{"models"},
			},
			want:    &expected,
			wantErr: false,
		},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got, err := GetModelsFromSpecification(tt.args.contract, tt.args.pathToModels)
			if (err != nil) != tt.wantErr {
				t.Errorf("GetModelsFromSpecification() error = %v, wantErr %v", err, tt.wantErr)
				return
			}
			if !reflect.DeepEqual(got, tt.want) {
				t.Errorf("GetModelsFromSpecification() got = %v, want %v", got, tt.want)
			}
		})
	}
}
