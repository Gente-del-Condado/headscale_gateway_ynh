package main

import (
	"os"
	"regexp"
	"strings"
)

var requestedNodeNamePattern = regexp.MustCompile(`^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$`)

func validRequestedNodeName(name string) bool {
	return requestedNodeNamePattern.MatchString(name) && !strings.Contains(name, "--")
}

// proposedNodeName solo propone un nombre. No registra un nodo ni sustituye la
// identidad persistida; la confirmación del administrador se guarda en SQLite.
func proposedNodeName() string {
	host, _ := os.Hostname()
	host = normalizeDNSName(host)
	if len(host) > 63 {
		host = host[:63]
	}
	for len(host) > 0 && host[len(host)-1] == '-' {
		host = host[:len(host)-1]
	}
	if !validRequestedNodeName(host) {
		return "gateway"
	}
	return host
}
