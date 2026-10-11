FROM golang:1.26-alpine AS build
WORKDIR /src
COPY go.mod main.go ./
RUN CGO_ENABLED=0 go build -trimpath -ldflags="-s -w" -o /app .

FROM alpine:3.22
# preStop 훅의 sleep 을 쓰려고 셸이 있는 alpine 을 쓴다
COPY --from=build /app /app
USER 65534
ENTRYPOINT ["/app"]
