// Comprime con el algoritmo de la versión Go fijada por el proyecto, sin
// depender de las variantes de zlib que utiliza Python en cada distribución.
package main

import (
	"compress/gzip"
	"io"
	"log"
	"os"
)

func main() {
	if len(os.Args) != 3 {
		log.Fatal("uso: deterministic_gzip entrada.tar salida.tar.gz")
	}
	in, err := os.Open(os.Args[1])
	if err != nil {
		log.Fatal(err)
	}
	defer in.Close()
	out, err := os.Create(os.Args[2])
	if err != nil {
		log.Fatal(err)
	}
	w, err := gzip.NewWriterLevel(out, gzip.BestCompression)
	if err != nil {
		log.Fatal(err)
	}
	if _, err = io.Copy(w, in); err != nil {
		log.Fatal(err)
	}
	if err = w.Close(); err != nil {
		log.Fatal(err)
	}
	if err = out.Close(); err != nil {
		log.Fatal(err)
	}
}
