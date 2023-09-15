package main

import (
	"fmt"
	"github.com/pkg/browser"
	"net/http"
	"net/url"
	"os"
)

func Open(dataContractFileName string, dataContractStudioUrl string) error {
	file, err := os.ReadFile(dataContractFileName)
	if err != nil {
		return err
	}

	//r, err := http.PostForm(dataContractStudioUrl+"/new", url.Values{})
	//strings := strings.Split(r.Request.URL.String(), "/")
	//length := len(strings)
	//id := strings[length-2]
	id := "f5b27004-5299-4331-94d1-414ee8cd5bb2"

	fmt.Println(id)

	yaml := url.QueryEscape(string(file))
	contractUrl := dataContractStudioUrl + "/" + id
	formUrl := contractUrl +"/save"

	fmt.Println(formUrl)

	response, err := http.PostForm(formUrl, url.Values{"yaml": {yaml}})

	fmt.Println(response.Status)

	err = browser.OpenURL(contractUrl)

	if err != nil {
		return err
	}


	return nil
}
