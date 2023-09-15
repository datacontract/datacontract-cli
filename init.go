package main

import (
	"fmt"
	"io"
	"net/http"
	"os"
)

const initTemplateUrl = "https://datacontract.com/datacontract.init.yaml"
const targetFileName = "datacontract.yml"

func Init() error {
	response, err := fetchInitTemplate()
	if err != nil {
		return err
	}

	body, err := readInitTemplate(response, err)
	if err != nil {
		return err
	}

	os.WriteFile(targetFileName, body, os.ModePerm)

	return nil
}

func readInitTemplate(response *http.Response, err error) ([]byte, error) {
	defer response.Body.Close()

	body, err := io.ReadAll(response.Body)

	if err != nil {
		return nil, fmt.Errorf("failed to read init template: %w", err)
	}
	return body, nil
}

func fetchInitTemplate() (*http.Response, error) {
	response, err := http.Get(initTemplateUrl)

	if err != nil {
		return nil, fmt.Errorf("failed to fetch init template: %w", err)
	}

	if !(response.StatusCode >= 200 && response.StatusCode < 300) {
		return nil, fmt.Errorf("failed to fetch init template: %v", response.Status)
	}

	return response, nil
}
