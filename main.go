package main

import "log"

func main() {
	err := Init()

	if err != nil {
		log.Fatal(err)
	}
}
