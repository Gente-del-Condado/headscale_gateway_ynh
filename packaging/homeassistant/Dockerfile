FROM golang:1.27.4-alpine AS build
WORKDIR /src
ADD source.tar.gz /src/
RUN CGO_ENABLED=0 go build -mod=readonly -buildvcs=false -trimpath -o /out/headscale-gateway .

FROM python:3.14-alpine3.24
ARG BUILD_VERSION
ARG BUILD_ARCH
LABEL org.opencontainers.image.authors="Gente del Condado <headscale-gateway@gentedelcondado.es>" org.opencontainers.image.documentation="https://gente-del-condado.github.io/headscale_gateway_ynh/HOME_ASSISTANT.html"
LABEL io.hass.type="app" io.hass.version="${BUILD_VERSION}" io.hass.arch="${BUILD_ARCH}"
COPY --from=build /usr/local/go/lib/time/zoneinfo.zip /usr/share/zoneinfo.zip
ENV ZONEINFO=/usr/share/zoneinfo.zip PYTHONDONTWRITEBYTECODE=1
COPY --from=build /out/headscale-gateway /usr/local/bin/headscale-gateway
COPY --from=build /src/VERSION /usr/share/headscale-gateway/VERSION
COPY notices/ /usr/share/licenses/headscale-gateway/
COPY run.py hgw_bootstrap.py /usr/local/lib/headscale-gateway/
ENTRYPOINT ["python3", "/usr/local/lib/headscale-gateway/run.py"]
