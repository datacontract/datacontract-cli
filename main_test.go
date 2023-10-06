package main

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
			t.Errorf(`Breaking() gotOutput
---
%v
---
wantOutput
---
%v
---`, buf.String(), test.wantOutput)
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
