package main

import (
	"fmt"
	"os"
	"path/filepath"
	"log"
	"code.cloudfoundry.org/bytefmt"
)

func BrowseDir(dirname string) error {
	// Display the content of the directory
	err := filepath.Walk(dirname,
		func(path string, info os.FileInfo, err error) error {
			if err != nil {
				fmt.Println(err)
				return err
			}

			fileobjSizeInt64 := info.Size()
			fileobjSizeUInt64 := uint64(fileobjSizeInt64)
			fileobjSizeHuman := ""
			fileobjModTime := ""
			namewdir := path
			if (info.IsDir()) {
				namewdir += "/"
			} else {
				fileobjSizeHuman = bytefmt.ByteSize(fileobjSizeUInt64)
				fileobjModTime = info.ModTime().Format("2006-01-02 15:04")
			}
			log.Printf("%s %s %s\n", namewdir, fileobjModTime, fileobjSizeHuman)
			return nil
		})
	return err
}

