import argparse
import os
import sys
from pathlib import Path

import uvicorn
from pydantic import ValidationError


VALID_ENVS = ("dev", "test", "prod")
DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent / "config.yaml"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="启动 Pivot 后端服务")
    parser.add_argument(
        "--env",
        choices=VALID_ENVS,
        default="dev",
        help="运行环境，支持 dev、test、prod，默认 dev；配置统一从 YAML 读取",
    )
    parser.add_argument(
        "--config",
        default=str(DEFAULT_CONFIG_PATH),
        help="YAML 配置文件路径，默认 src/config.yaml",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config_file = Path(args.config)
    if not config_file.is_file():
        print(f"配置文件不存在：{config_file}", file=sys.stderr)
        return 1

    os.environ["PIVOT_CONFIG_FILE"] = str(config_file)

    try:
        from src.core.config import settings
    except ValidationError as exc:
        print(f"配置校验失败：\n{exc}", file=sys.stderr)
        return 1

    uvicorn.run(
        "src.main:app",
        host=settings.server_host,
        port=settings.server_port,
        reload=args.env == "dev",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
