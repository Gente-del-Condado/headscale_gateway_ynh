//go:build linux && !android

package headscalecontrol

import (
	"bytes"
	"crypto/rand"
	"encoding/hex"
	"errors"
	"io"
	"os"
	"path/filepath"
	"strings"

	"golang.org/x/sys/unix"
)

type fileImage struct {
	Data    []byte `json:"data"`
	Mode    uint32 `json:"mode"`
	UID     int    `json:"uid"`
	GID     int    `json:"gid"`
	SELinux []byte `json:"selinux,omitempty"`
}

// Las carpetas del ayudante son root y no admiten escritura de otro usuario.
// Se recorren sin seguir enlaces, incluyendo los componentes ya existentes.
func ensureRootDir(path string, mode uint32) error {
	if !filepath.IsAbs(path) || filepath.Clean(path) != path {
		return errors.New("carpeta del controlador inválida")
	}
	fd, e := unix.Open("/", unix.O_RDONLY|unix.O_DIRECTORY|unix.O_CLOEXEC, 0)
	if e != nil {
		return e
	}
	for _, part := range strings.Split(strings.TrimPrefix(path, "/"), "/") {
		next, e := unix.Openat(fd, part, unix.O_RDONLY|unix.O_DIRECTORY|unix.O_NOFOLLOW|unix.O_CLOEXEC, 0)
		if e == unix.ENOENT {
			if e = unix.Mkdirat(fd, part, mode); e == nil {
				next, e = unix.Openat(fd, part, unix.O_RDONLY|unix.O_DIRECTORY|unix.O_NOFOLLOW|unix.O_CLOEXEC, 0)
			}
		}
		unix.Close(fd)
		if e != nil {
			return e
		}
		fd = next
		var stat unix.Stat_t
		if e = unix.Fstat(fd, &stat); e != nil || stat.Uid != 0 || stat.Mode&0022 != 0 {
			unix.Close(fd)
			return errors.New("carpeta del controlador con permisos inseguros")
		}
	}
	defer unix.Close(fd)
	var stat unix.Stat_t
	if e = unix.Fstat(fd, &stat); e != nil {
		return e
	}
	if stat.Mode&0777 != mode {
		return errors.New("modo inesperado de carpeta del controlador")
	}
	return nil
}

// parentDir fija cada componente mediante descriptores O_NOFOLLOW. Una carpeta
// intercambiada o un enlace simbólico no puede redirigir una escritura root.
func parentDir(path string) (*os.File, string, error) {
	if !filepath.IsAbs(path) || filepath.Clean(path) != path || path == "/" {
		return nil, "", errors.New("ruta local no canónica")
	}
	parts := strings.Split(strings.TrimPrefix(path, "/"), "/")
	fd, e := unix.Open("/", unix.O_RDONLY|unix.O_DIRECTORY|unix.O_CLOEXEC, 0)
	if e != nil {
		return nil, "", e
	}
	for _, part := range parts[:len(parts)-1] {
		next, e := unix.Openat(fd, part, unix.O_RDONLY|unix.O_DIRECTORY|unix.O_NOFOLLOW|unix.O_CLOEXEC, 0)
		unix.Close(fd)
		if e != nil {
			return nil, "", e
		}
		fd = next
	}
	return os.NewFile(uintptr(fd), filepath.Dir(path)), parts[len(parts)-1], nil
}

func readImage(path string) (fileImage, error) {
	return readImageLimit(path, MaxDocument)
}

func readImageLimit(path string, limit int64) (fileImage, error) {
	dir, name, e := parentDir(path)
	if e != nil {
		return fileImage{}, e
	}
	defer dir.Close()
	fd, e := unix.Openat(int(dir.Fd()), name, unix.O_RDONLY|unix.O_NOFOLLOW|unix.O_NONBLOCK|unix.O_CLOEXEC, 0)
	if e != nil {
		return fileImage{}, e
	}
	f := os.NewFile(uintptr(fd), name)
	defer f.Close()
	var stat unix.Stat_t
	if e = unix.Fstat(fd, &stat); e != nil {
		return fileImage{}, e
	}
	if stat.Mode&unix.S_IFMT != unix.S_IFREG || stat.Size > limit || stat.Mode&0002 != 0 || stat.Nlink != 1 {
		return fileImage{}, errors.New("archivo local inseguro o demasiado grande")
	}
	data, e := io.ReadAll(io.LimitReader(f, limit+1))
	if e != nil || int64(len(data)) > limit {
		return fileImage{}, errors.New("no se pudo leer el archivo local")
	}
	image := fileImage{Data: data, Mode: stat.Mode & 0777, UID: int(stat.Uid), GID: int(stat.Gid)}
	if size, e := unix.Fgetxattr(fd, "security.selinux", nil); e == nil && size > 0 && size < 4096 {
		image.SELinux = make([]byte, size)
		if _, e = unix.Fgetxattr(fd, "security.selinux", image.SELinux); e != nil {
			return fileImage{}, errors.New("no se pudo conservar el contexto SELinux")
		}
	}
	return image, nil
}

// writeImage conserva propietario, modo y contexto SELinux, y sincroniza el
// archivo y su directorio antes de devolver éxito. El temporal no sigue enlaces.
func writeImage(path string, image fileImage) error {
	dir, name, e := parentDir(path)
	if e != nil {
		return e
	}
	defer dir.Close()
	var random [16]byte
	if _, e = rand.Read(random[:]); e != nil {
		return e
	}
	temporary := ".hgw-control-" + hex.EncodeToString(random[:])
	fd, e := unix.Openat(int(dir.Fd()), temporary, unix.O_WRONLY|unix.O_CREAT|unix.O_EXCL|unix.O_NOFOLLOW|unix.O_CLOEXEC, 0600)
	if e != nil {
		return e
	}
	f := os.NewFile(uintptr(fd), temporary)
	defer func() { f.Close(); _ = unix.Unlinkat(int(dir.Fd()), temporary, 0) }()
	if _, e = io.Copy(f, bytes.NewReader(image.Data)); e != nil {
		return e
	}
	if e = unix.Fchown(fd, image.UID, image.GID); e != nil {
		return e
	}
	if e = unix.Fchmod(fd, image.Mode); e != nil {
		return e
	}
	if len(image.SELinux) > 0 {
		if e = unix.Fsetxattr(fd, "security.selinux", image.SELinux, 0); e != nil {
			return e
		}
	}
	if e = f.Sync(); e != nil {
		return e
	}
	if e = unix.Renameat(int(dir.Fd()), temporary, int(dir.Fd()), name); e != nil {
		return e
	}
	return dir.Sync()
}

func removeFile(path string) error {
	dir, name, e := parentDir(path)
	if e != nil {
		return e
	}
	defer dir.Close()
	if e = unix.Unlinkat(int(dir.Fd()), name, 0); e != nil {
		return e
	}
	return dir.Sync()
}
