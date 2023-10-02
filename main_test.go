package main

import (
	"net/http"
	"net/http/httptest"
	"testing"
)

var TestResourcesServer = httptest.NewServer(http.FileServer(http.Dir("./test_resources")))

func TestMain(m *testing.M) {
	defer TestResourcesServer.Close()

	m.Run()
}
