package main

import (
	"fmt"
	"github.com/pkg/browser"
	"log"
	"net/http"
	"net/url"
	"os"
	"strings"
)

func Open(dataContractFileName string, dataContractStudioUrl string) error {
	file, err := os.ReadFile(dataContractFileName)
	if err != nil {
		return err
	}

	id, err := newDataContractId(dataContractStudioUrl)
	if err != nil {
		return err
	}

	contractUrl, err := sendDataContract(dataContractStudioUrl, *id, file)
	if err != nil {
		return err
	}

	err = openDataContractInBrowser(*contractUrl)
	if err != nil {
		return err
	}

	return nil
}

func newDataContractId(dataContractStudioUrl string) (*string, error) {
	r, err := postForm(dataContractStudioUrl+"/new", nil)
	if err != nil {
		return nil, fmt.Errorf("failed to create new data contract id: %w", err)
	}

	strings := strings.Split(r.Request.URL.Path, "/")

	if len(strings) < 2 {
		return nil, fmt.Errorf("cant extract data contract id from %v", r.Request.URL.Path)
	}

	return &strings[len(strings)-2], nil
}

func sendDataContract(dataContractStudioUrl string, id string, file []byte) (*string, error) {
	contractUrl := dataContractStudioUrl + "/" + id

	_, err := postForm(contractUrl+"/save", url.Values{"yaml": {string(file)}})
	if err != nil {
		return nil, fmt.Errorf("failed to send data contract: %w", err)
	}

	return &contractUrl, nil
}

func openDataContractInBrowser(contractUrl string) error {
	log.Println("🌐 opening data contract at " + contractUrl)
	err := browser.OpenURL(contractUrl)
	return err
}

func postForm(formUrl string, formData url.Values) (*http.Response, error) {
	response, err := http.PostForm(formUrl, formData)
	defer response.Body.Close()

	if err != nil {
		return nil, fmt.Errorf("form post to %v failed: %w", formUrl, err)
	}

	if !(response.StatusCode >= 200 && response.StatusCode < 300) {
		return nil, fmt.Errorf("form post to %v failed: %v", formUrl, response.Status)
	}

	return response, nil
}
