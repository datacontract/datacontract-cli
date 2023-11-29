package datacontract

import (
	"io"
	"log"
	"os"
	"strings"
)

func Log(target io.Writer, output string, v ...any) {
	log.SetOutput(target)
	log.Printf(strings.TrimSpace(output), v...)
	log.SetOutput(os.Stderr)
}
