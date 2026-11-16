Headscale Gateway provides private HTTPS access to applications and services on
your server or local network through an existing Headscale network. It combines
a VPN node with a reverse proxy, DNS and certificate management, access settings,
configuration profiles and encrypted backups in one web interface.

The YunoHost package integrates administrator access with the portal's single
sign-on and supports multiple instances, upgrades, URL changes, backups and
restoration. It does not open an additional public inbound port.

An existing Headscale coordination server is required. The portal's HTTPS
domain and the private domain used by the Gateway are independent settings.

The shared dashboard highlights the main service domain as a clickable link in
Overview / Status. The administration URL is shown separately; YunoHost SSO
does not itself provide browser connectivity to the private service network.

The original code is licensed under AGPL-3.0-only. Public release resources
provide the corresponding complete server sources and Go dependencies, with
build instructions and checksums. The package preserves third-party notices.
