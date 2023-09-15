package main

import (
	"fmt"
	"io"
	"net/http"
	"os"
)

func Init(fileName string, initTemplateUrl string) error {
	response, err := fetchInitTemplate(initTemplateUrl)
	if err != nil {
		return err
	}

	body, err := readInitTemplate(response, err)
	if err != nil {
		return err
	}

	err = writeFile(fileName, body)
	if err != nil {
		return err
	}

	return nil
}

func writeFile(name string, body []byte) error {
	err := os.WriteFile(name, body, os.ModePerm)

	if err != nil {
		return fmt.Errorf("failed to write %v: %w", dataContractFileName, err)
	}

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

func fetchInitTemplate(url string) (*http.Response, error) {
	response, err := http.Get(url)

	if err != nil {
		return nil, fmt.Errorf("failed to fetch init template: %w", err)
	}

	if !(response.StatusCode >= 200 && response.StatusCode < 300) {
		return nil, fmt.Errorf("failed to fetch init template: %v", response.Status)
	}

	return response, nil
}
