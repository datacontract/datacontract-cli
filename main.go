package main

import "fmt"

func main() {
	dataProductUrl := "https://api.datamesh-manager.com/api/dataproducts/stock_updated"
	outputPortId := "glue_catalog_database_stock_updated_v1"
	headers := make([][]string, 1)
	apiKeyHeader := make([]string, 2)
	apiKeyHeader[0] = "x-api-key"
	apiKeyHeader[1] = "dmm_live_jRtdtLtL4uwChLp42tqIG6uR4Z5LzbDFDxHFXZ2snPo4YDzzQrZZhsKMPTGX6wLN"
	headers[0] = apiKeyHeader

	opSchemaConfig := &OutputPortSchemaConfiguration{
		url:     dataProductUrl,
		id:      outputPortId,
		headers: &headers,
	}

	err := Init("0.0.1", "", opSchemaConfig)
	if err != nil {
		fmt.Println(err)
	}
}
