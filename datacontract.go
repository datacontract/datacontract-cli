package main

type DataContract struct {
	DataContractSpecification string
	Info                      struct {
		Id        string
		Purpose   *string
		Status    *string // Typical values are: draft, requested, approved, rejected, canceled
		StartDate *string
		EndDate   *string
	}
	Provider struct {
		TeamId          string
		TeamName        *string
		DataProductId   string
		DataProductName *string
		OutputPortId    string
		OutputPortName  *string
	}
	Consumer struct {
		TeamId          string
		TeamName        *string
		DataProductId   *string
		DataProductName *string
	}
	Terms struct {
		Usage                *string
		Limitations          *string
		Billing              *string
		NoticePeriod         *string // ISO-8601
		IndividualAgreements *string
	}
	Schema *struct {
		Type          string // Typical values are: dbt, bigquery, jsonschema, openapi, protobuf, paypal, custom
		Specification string
	}
	Tags   *[]string
	Links  *map[string]string
	Custom *map[string]string
}
