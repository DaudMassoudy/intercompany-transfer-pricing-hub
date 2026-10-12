from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')
    app_version: str = '2.4.0-rc.3-hotfix7'
    demo_mode: bool = True
    database_url: str = 'sqlite:///./otp.db'
    redis_url: str = 'redis://localhost:6379/0'
    jwt_secret: str = 'dev-only-change-me'
    jwt_issuer: str = 'enterprise-otp'
    access_token_minutes: int = 60
    n8n_integration_key: str = 'demo-n8n-change-me'
    oidc_enabled: bool = False
    oidc_issuer: str | None = None
    oidc_client_id: str | None = None
    oidc_audience: str | None = None
    ai_provider: str = 'deterministic'
    ai_model: str = 'grounded-explainer-v2'
    cors_origins: str = 'http://localhost:3000'
    environment: str = 'demo'

    @model_validator(mode='after')
    def validate_production_safety(self):
        if self.environment.lower() == 'production':
            unsafe = {'', 'dev-only-change-me', 'demo_jwt_secret_change_me', 'SET_IN_SECRET_MANAGER'}
            if self.demo_mode:
                raise ValueError('DEMO_MODE must be false in production')
            if self.jwt_secret in unsafe or len(self.jwt_secret) < 32:
                raise ValueError('Production JWT_SECRET must be a non-placeholder secret of at least 32 characters')
            if self.n8n_integration_key in unsafe or len(self.n8n_integration_key) < 32:
                raise ValueError('Production N8N_INTEGRATION_KEY must be a non-placeholder secret of at least 32 characters')
            origins=[x.strip() for x in self.cors_origins.split(',') if x.strip()]
            if not origins or any(o == '*' for o in origins):
                raise ValueError('Production CORS_ORIGINS must explicitly enumerate trusted origins')
        return self


settings = Settings()
