.PHONY: wire build test lint run

wire:
	go generate ./cmd/...

build:
	go build ./...

test:
	go test ./... -v -count=1

lint:
	golangci-lint run ./...

run:
	go run ./cmd/...
