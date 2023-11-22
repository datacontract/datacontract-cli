package datacontract

import (
	"errors"
	"fmt"
	"gopkg.in/yaml.v3"
	"io"
	"net/http"
	"os"
	"reflect"
	"strings"
)

const StringReferencePrefix = "$ref:"
const ObjectReferenceKey = "$ref"

func IsReference(reference any) bool {
	if text, ok := reference.(string); ok {
		return strings.HasPrefix(text, StringReferencePrefix)
	}

	if obj, ok := reference.(map[string]any); ok {
		return obj[ObjectReferenceKey] != nil
	}

	return false
}

func ResolveReference(contract DataContract, reference any) (_ any, err error) {
	if text, ok := reference.(string); ok {
		return resolveStringReference(text)
	}

	if obj, ok := reference.(map[string]any); ok {
		if objReference, ok := obj[ObjectReferenceKey].(string); ok {
			return resolveObjectReference(objReference, contract)
		}
	}

	return nil, fmt.Errorf("can't resolve reference for type %v", reflect.TypeOf(reference))
}

func resolveStringReference(reference string) (any, error) {
	cleanReference := strings.Trim(strings.TrimPrefix(reference, StringReferencePrefix), " ")

	bytes, err := resolveFile(cleanReference)
	if err != nil {
		return "", err
	}

	return string(bytes), nil
}

func resolveObjectReference(reference string, contract DataContract) (any, error) {
	segments := strings.Split(reference, "#")

	document, err := resolveDocument(segments, contract)
	if err != nil {
		return nil, err
	}

	path := getPath(segments)

	// prevent accidentally referencing root in same file
	if strings.HasPrefix(reference, "#") && len(path) < 1 {
		return nil, nil
	}

	field, err := GetValue(document, path)
	if err != nil {
		return nil, err
	}

	return enforceMap(field)
}

func enforceMap(entity any) (map[string]any, error) {
	if anyMap, ok := entity.(map[string]any); !ok {
		return nil, errors.New("referenced value is not an object")
	} else {
		return anyMap, nil
	}
}

func getPath(segments []string) []string {
	if len(segments) < 2 {
		return []string{}
	} else {
		pathString := strings.TrimPrefix(segments[1], "/")
		split := strings.Split(pathString, "/")
		var path []string

		for _, s := range split {
			if s != "" {
				path = append(path, s)
			}
		}

		return path
	}
}

func resolveDocument(segments []string, contract DataContract) (map[string]any, error) {
	if segments[0] == "" {
		return contract, nil
	} else {
		bytes, err := resolveFile(segments[0])
		if err != nil {
			return nil, err
		}

		objectFromFile := map[string]any{}

		err = yaml.Unmarshal(bytes, objectFromFile)
		if err != nil {
			return nil, err
		}

		return objectFromFile, nil
	}
}

func resolveFile(reference string) (bytes []byte, err error) {
	if IsURI(reference) {
		bytes, err = resolveFileFromRemote(reference)
	} else {
		bytes, err = resolveFileLocally(reference)
	}

	if err != nil {
		return nil, fmt.Errorf("can't resolve reference '%v': %w", reference, err)
	}

	return bytes, nil
}

func resolveFileLocally(path string) ([]byte, error) {
	return os.ReadFile(path)
}

func resolveFileFromRemote(url string) ([]byte, error) {
	response, err := http.Get(url)
	defer response.Body.Close()

	if err != nil {
		return nil, err
	}

	return io.ReadAll(response.Body)
}
