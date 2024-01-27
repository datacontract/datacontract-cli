import requests


def fetch_schema():
    schema_url = "https://datacontract.com/datacontract.schema.json"
    response = requests.get(schema_url)
    return response.json()
