from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "mysql+pymysql://pivot:pivot_pass_2026@localhost:3306/pivot"
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    model_config = {"env_file": ".env", "env_prefix": "PIVOT_"}


settings = Settings()
