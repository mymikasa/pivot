.PHONY: help up down migrate seed db-setup backend frontend dev test test-backend test-frontend lint build

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

up:
	docker compose up -d

down:
	docker compose down

migrate:
	uv run alembic upgrade head

seed:
	uv run python -m src.seed

db-setup: migrate seed

dev:
	docker compose up -d
	@sleep 3
	uv run python -m src.cli --env dev & sleep 2 && cd frontend && npm run dev

backend:
	uv run python -m src.cli --env dev

frontend:
	cd frontend && npm run dev

test: test-backend test-frontend

test-backend:
	uv run pytest -v

test-frontend:
	cd frontend && npm run build

build:
	cd frontend && npm run build

lint:
	uv run ruff check .
