package main

import (
	"bytes"
	"log"
	"net/http"
	"net/http/httptest"
	"os"
	"testing"
)

var TestResourcesServer = httptest.NewServer(http.FileServer(http.Dir("./test_resources")))

func TestMain(m *testing.M) {
	defer TestResourcesServer.Close()

	m.Run()
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
			t.Errorf("Breaking() gotOutput %v, wantOutput %v", buf.String(), test.wantOutput)
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
