package datacontract

import (
	"fmt"
	"os"
	"testing"
)

func TestInit(t *testing.T) {
	templateUrl := fmt.Sprintf("%v/init/datacontract_template.yaml", TestResourcesServer.URL)
	existingFile := CreateTmpFileName()

	type args struct {
		fileName        string
		initTemplateUrl string
		overwriteFile   bool
	}
	tests := []struct {
		name    string
		args    args
		wantErr bool
	}{
		{
			name: "write-file",
			args: args{
				fileName:        CreateTmpFileName(),
				initTemplateUrl: templateUrl,
				overwriteFile:   false,
			},
			wantErr: false,
		},
		{
			name: "file-exists",
			args: args{
				fileName:        existingFile,
				initTemplateUrl: templateUrl,
				overwriteFile:   false,
			},
			wantErr: true,
		},
		{
			name: "overwrite-file",
			args: args{
				fileName:        CreateTmpFileName(),
				initTemplateUrl: templateUrl,
				overwriteFile:   true,
			},
			wantErr: false,
		},
	}
	for _, tt := range tests {
		os.WriteFile(existingFile, []byte{}, os.ModePerm)

		t.Run(tt.name, func(t *testing.T) {
			if err := Init(tt.args.fileName, tt.args.initTemplateUrl, tt.args.overwriteFile); (err != nil) != tt.wantErr {
				t.Errorf("Init() error = %v, wantErr %v", err, tt.wantErr)
			} else if err == nil {
				generated, _ := os.ReadFile(tt.args.fileName)
				expected, _ := os.ReadFile("test_resources/init/datacontract_template.yaml")

				if string(generated) != string(expected) {
					t.Errorf("Init() gotFile = %v, wantFile %v", string(generated), string(expected))
				}
			}
		})
	}
}
