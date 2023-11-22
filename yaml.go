package datacontract

import (
	"bytes"
	"gopkg.in/yaml.v3"
)

func ToYaml(object any) (result []byte, err error) {
	var b bytes.Buffer

	encoder := yaml.NewEncoder(&b)
	encoder.SetIndent(2)

	err = encoder.Encode(object)
	if err != nil {
		return nil, err
	}

	return b.Bytes(), nil
}
