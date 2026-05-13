UV ?= uv
PY_ENV ?= dev
PY_CONFIG ?= src/config.yaml
PYTEST_ARGS ?=
ALEMBIC_REVISION ?= head

.PHONY: help up down migrate seed db-setup backend frontend dev test test-backend test-frontend lint build python-sync python-run python-dev python-test python-test-file python-migrate python-seed python-db-setup python-compile

help:
	@echo "Pivot 开发命令："
	@echo ""
	@echo "  make dev          启动全栈开发环境（MySQL + 后端 + 前端）"
	@echo "  make up           启动 MySQL"
	@echo "  make down         停止 MySQL"
	@echo "  make db-setup     执行迁移 + seed（首次使用）"
	@echo "  make migrate      执行数据库迁移"
	@echo "  make seed         执行 seed 脚本"
	@echo "  make backend      启动后端"
	@echo "  make frontend     启动前端"
	@echo "  make test         运行全部测试"
	@echo "  make test-backend 运行后端测试"
	@echo "  make test-frontend 运行前端测试"
	@echo "  make build        构建前端"
	@echo "  make lint         运行后端 lint"
	@echo ""
	@echo "Python 后端命令："
	@echo "  make python-sync      安装/同步 Python 依赖"
	@echo "  make python-run       启动 Python 后端（PY_CONFIG=src/config.yaml）"
	@echo "  make python-dev       以 dev 环境启动 Python 后端"
	@echo "  make python-test      运行 Python 测试（PYTEST_ARGS 可追加参数）"
	@echo "  make python-test-file 运行单个测试文件（FILE=tests/xxx.py）"
	@echo "  make python-migrate   执行 Alembic 迁移（ALEMBIC_REVISION=head）"
	@echo "  make python-seed      执行 Python seed"
	@echo "  make python-db-setup  执行迁移 + seed"
	@echo "  make python-compile   编译检查 src/tests"

up:
	docker compose up -d

down:
	docker compose down

migrate:
	$(MAKE) python-migrate

seed:
	$(MAKE) python-seed

db-setup: migrate seed

dev:
	docker compose up -d
	@sleep 3
	$(UV) run python -m src.cli --env dev & sleep 2 && cd frontend && npm run dev

backend:
	$(MAKE) python-run PY_ENV=dev

frontend:
	cd frontend && npm run dev

test: test-backend test-frontend

test-backend:
	$(MAKE) python-test

test-frontend:
	cd frontend && npm run build

build:
	cd frontend && npm run build

lint:
	$(UV) run ruff check .

python-sync:
	$(UV) sync

python-run:
	$(UV) run python -m src.cli --env $(PY_ENV) --config $(PY_CONFIG)

python-dev:
	$(MAKE) python-run PY_ENV=dev

python-test:
	$(UV) run pytest -v $(PYTEST_ARGS)

python-test-file:
	@test -n "$(FILE)" || (echo "请指定 FILE=tests/path/to_test.py" && exit 1)
	$(UV) run pytest $(FILE) -v $(PYTEST_ARGS)

python-migrate:
	$(UV) run alembic upgrade $(ALEMBIC_REVISION)

python-seed:
	$(UV) run python -m src.seed

python-db-setup: python-migrate python-seed

python-compile:
	$(UV) run python -m compileall src tests
