package main

import "fmt"

func main() {
	err := Init("0.0.1", "")
	if err != nil {
		fmt.Println(err)
	}
}
