package datacontract

import (
	"bytes"
	"fmt"
	"log"
	"math/rand"
	"net/http"
	"net/http/httptest"
	"os"
	"testing"
)

var TestResourcesServer = httptest.NewServer(http.FileServer(http.Dir("./test_resources")))
var TmpFolder = "tmp"

func TestMain(m *testing.M) {
	// start static file server
	defer TestResourcesServer.Close()

	// create folder for temporary files
	os.Mkdir(TmpFolder, os.ModePerm)

	// run test
	m.Run()

	// delete temporary files
	os.RemoveAll(TmpFolder)
}

func CreateTmpFileName() string {
	return fmt.Sprintf("tmp/%v.yaml", rand.Int())
}

func RunLogOutputTest[T any](t *testing.T, test LogOutputTest[T], functionName string, function func() error) {
	var buf bytes.Buffer
	log.SetFlags(0)
	log.SetOutput(&buf)

	t.Run(test.name, func(t *testing.T) {
		if err := function(); (err != nil) != test.wantErr {
			t.Errorf("%v() error = %v, wantErr %v", functionName, err, test.wantErr)
		}
		if buf.String() != test.wantOutput {
			t.Errorf(`%v() gotOutput
---
%v
---
wantOutput
---
%v
---`, functionName, buf.String(), test.wantOutput)
		}
	})

	log.SetOutput(os.Stderr)
}

type LogOutputTest[T any] struct {
	name       string
	args       T
	wantErr    bool
	wantOutput string
}

func RunFileWriteTest[T any](t *testing.T, test FileWriteTest[T], functionName string, originalFileLocation string, function func(tempFileName string) error) {
	tmpFile, _ := os.CreateTemp("", functionName)
	input, _ := os.ReadFile(originalFileLocation)
	os.WriteFile(tmpFile.Name(), input, os.ModePerm)

	t.Run(test.name, func(t *testing.T) {
		if err := function(tmpFile.Name()); (err != nil) != test.wantErr {
			t.Errorf("%v() error = %v, wantErr %v", functionName, err, test.wantErr)
		}

		generated, _ := os.ReadFile(tmpFile.Name())
		expected, _ := os.ReadFile(test.expectedFileLocation)

		if string(generated) != string(expected) {
			t.Errorf("%v() gotFile = %v, wantFile %v", functionName, string(generated), string(expected))
		}
	})

	tmpFile.Close()

}

type FileWriteTest[T any] struct {
	name                 string
	args                 T
	wantErr              bool
	expectedFileLocation string
}
