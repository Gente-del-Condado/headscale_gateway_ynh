//go:build !windows

package main

import "errors"

func platformServiceEntrypoint(string, func()) (bool, error) {
	return true, errors.New("--windows-service solo está disponible en Windows")
}
