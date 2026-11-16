//go:build !linux || android

package headscalecontrol

import "errors"

func RunController([]string) error {
	return errors.New("el ayudante local requiere Linux; este sistema puede administrar un controlador remoto")
}
