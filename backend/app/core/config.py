from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = "development"

    database_url: str = "postgresql+psycopg://pitchleague:pitchleague@localhost:5432/pitchleague"

    auth_shared_secret: str = "change-me-to-a-long-random-string"
    jwt_algorithm: str = "HS256"
    backend_cors_origins: str = "http://localhost:3000"

    odds_provider: str = "mock"
    the_odds_api_key: str = ""
    the_odds_api_base_url: str = "https://api.the-odds-api.com/v4"

    ai_insights_provider: str = "heuristic"
    anthropic_api_key: str = ""

    default_gameweek_budget: int = 10_000

    # Comma-separated emails granted the platform-level system admin panel
    # on sign-in — there's no in-app role-granting UI, so this is the
    # bootstrap. See core/security.py.
    staff_emails: str = ""

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.backend_cors_origins.split(",") if origin.strip()]

    @property
    def staff_email_set(self) -> set[str]:
        return {e.strip().lower() for e in self.staff_emails.split(",") if e.strip()}


@lru_cache
def get_settings() -> Settings:
    return Settings()
