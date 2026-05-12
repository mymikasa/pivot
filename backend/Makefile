SVC ?= user

.PHONY: proto tidy clean wire build test lint run all

# proto: buf lint + generate (全局)
proto:
	buf lint
	buf generate

# tidy: sync dependencies
tidy:
	go mod tidy

# clean: 清除生成产物
clean:
	rm -rf api/gen/

# 以下委托到 app/$(SVC)/Makefile
wire build test lint run:
	$(MAKE) -C app/$(SVC) $@

# all: full pipeline for one service
all: tidy proto wire build test
