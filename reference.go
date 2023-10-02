package main

import (
	"fmt"
	"io"
	"net/http"
	"os"
	"strings"
)

const ReferencePrefix = "$ref:"

func IsReference(text string) bool {
	return strings.HasPrefix(text, ReferencePrefix)
}

func ResolveReference(reference string) (_ string, err error) {
	var bytes []byte
	cleanReference := strings.Trim(strings.TrimPrefix(reference, ReferencePrefix), " ")

	if IsURI(reference) {
		bytes, err = resolveReferenceFromRemote(cleanReference)
	} else {
		bytes, err = resolveReferenceLocally(cleanReference)
	}

	if err != nil {
		return "", fmt.Errorf("can't resolve reference '%v': %w", reference, err)
	}

	return string(bytes), nil
}

func resolveReferenceLocally(reference string) ([]byte, error) {
	return os.ReadFile(reference)
}

func resolveReferenceFromRemote(reference string) ([]byte, error) {
	response, err := http.Get(reference)
	defer response.Body.Close()

	if err != nil {
		return nil, err
	}

	return io.ReadAll(response.Body)
}
