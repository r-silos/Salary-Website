from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql+psycopg2://salary:salary@localhost:5432/salary"
    lca_min_sample: int = 30
    lca_wage_min: float = 20_000
    lca_wage_max: float = 500_000


settings = Settings()
