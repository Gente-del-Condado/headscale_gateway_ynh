# Procedencia del proveedor Technitium para ACME

Código MIT de https://github.com/ad-on-is/caddy-dns-technitium, versión `v0.1.0`.
Se conservan sin modificar `client.go`, `technitium.go`, sus pruebas y `LICENSE`.
Se omite `module.go`: registra un módulo Caddy y hace que Caddy se apropie del
SCM en Windows durante `init()`. Gateway solo necesita la interfaz libdns para
CertMagic y mantiene su propio ciclo de vida del servicio. No se cambia la API
Technitium ni el formato de los desafíos DNS-01.

Sumas originales:

`3bf9269d4ffec648453b061a74f35bf0e055fd117278e7a4b72e00e7424c73ec  client.go`
`143933e77d8a4e8a2dc20d4ffa76dcdf3537188c14c53d786a299dbcd769abc4  technitium.go`
`a98aea766f6d61b4449464b16988f6d8973a6fe74025a71ebe73ac9bb022cc06  technitium_test.go`
`2bfbb7f573fa321cad4e71c8415dcc9e6d6e8584acd4d673cebcc2dcc2fcce9d  LICENSE`
