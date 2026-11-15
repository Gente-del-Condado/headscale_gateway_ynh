//go:build !linux

package main

import "net"

func publishDesktopAdminAddress(net.Addr) {}
