"""Application configuration loaded from environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql://crawler:crawler@db:5432/building_orders"

    # Target website
    base_url: str = (
        "https://www.nsw.gov.au/departments-and-agencies/"
        "building-commission/register-of-building-work-orders"
    )

    # Email
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    email_from: str = ""
    email_to: str = ""

    # Scheduler
    crawl_interval_minutes: int = 60

    # Dashboard
    dashboard_port: int = 8080

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
