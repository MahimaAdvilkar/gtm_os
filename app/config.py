from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    anthropic_api_key: str = ""
    apify_api_key: str = ""
    apify_user_id: str = ""
    kalibr_api_key: str = ""
    kalibr_tenant_id: str = ""
    minds_ai_api_key: str = ""
    minds_ai_base_url: str = ""
    hubspot_api_key: str = ""
    hubspot_portal_id: str = ""
    app_env: str = "development"
    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
