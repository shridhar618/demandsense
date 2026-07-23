"""
Central application configuration.

DATABASE_URL defaults to a local SQLite file so the platform runs with zero
external dependencies. Setting DATABASE_URL to a Postgres DSN (as done in
docker-compose.yml) switches the whole app to Postgres with no code changes,
since all access goes through SQLAlchemy's engine abstraction.
"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "DemandSense AI"
    api_v1_prefix: str = "/api/v1"

    database_url: str = "sqlite:///./demandsense.db"

    # CORS - allow the Vite dev server by default
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    # Forecasting defaults
    default_forecast_horizon_days: int = 30
    min_history_days_required: int = 30

    class Config:
        env_file = ".env"


settings = Settings()
