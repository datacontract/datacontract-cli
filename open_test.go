package main

import (
	"fmt"
	"net/http"
	"net/http/httptest"
	"os"
	"reflect"
	"testing"
)

func Test_createDataContractInStudio(t *testing.T) {
	dataContractStudioId := "my-data-contract-id"
	dataContract, _ := os.ReadFile("test_resources/open/datacontract.yaml")

	studioMock := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		switch r.URL.String() {
		case "/new":
			if r.Method == http.MethodPost {
				redirectUrl := fmt.Sprintf("%v/%v/edit", r.URL.Host, dataContractStudioId)
				http.Redirect(w, r, redirectUrl, http.StatusFound)
				return
			}
		case fmt.Sprintf("/%v/edit", dataContractStudioId):
			if r.Method == http.MethodGet {
				w.WriteHeader(http.StatusCreated)
				return
			}
		case fmt.Sprintf("/%v/save", dataContractStudioId):
			if r.Method == http.MethodPost &&
				r.Header.Get("Content-Type") == "application/x-www-form-urlencoded" &&
				r.FormValue("yaml") == string(dataContract) {
				w.WriteHeader(http.StatusNoContent)
				return
			}
		default:
			w.WriteHeader(http.StatusBadRequest)
		}
	}))

	defer studioMock.Close()

	type args struct {
		dataContractFileName  string
		dataContractStudioUrl string
	}
	tests := []struct {
		name    string
		args    args
		want    string
		wantErr bool
	}{
		{
			name: "open",
			args: args{
				dataContractFileName:  "test_resources/open/datacontract.yaml",
				dataContractStudioUrl: studioMock.URL,
			},
			want:    fmt.Sprintf("%v/%v", studioMock.URL, dataContractStudioId),
			wantErr: false,
		},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got, err := createDataContractInStudio(tt.args.dataContractFileName, tt.args.dataContractStudioUrl)
			if (err != nil) != tt.wantErr {
				t.Errorf("createDataContractInStudio() error = %v, wantErr %v", err, tt.wantErr)
				return
			}
			if !reflect.DeepEqual(got, tt.want) {
				t.Errorf("createDataContractInStudio() got = %v, want %v", got, tt.want)
			}
		})
	}
}
