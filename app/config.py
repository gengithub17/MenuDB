import os

class Config:
    """Base configuration"""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

    # Database
    DATABASE_PATH = os.environ.get('DATABASE_PATH', 'data/menudb.db')
    SQLALCHEMY_DATABASE_URI = f'sqlite:///{DATABASE_PATH}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # WTF
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600  # 1 hour

    # App settings
    ITEMS_PER_PAGE = 10
    MAX_GENRES_PER_DISH = 2
    MAX_INGREDIENTS_PER_DISH = 10
    MAX_MEMO_LENGTH = 500

    # Default search settings (used when no query params / no per-user setting)
    DEFAULT_SEARCH_MODE = 'fuzzy'

    # API key (Feature: /api/v1 access)
    API_KEY_EXPIRY_HOURS = 1

    # Bookmarks ("want to cook" list) auto-expire after this many days
    BOOKMARK_EXPIRY_DAYS = 7

    # JWT verification (optional, opt-in defense-in-depth on top of the
    # X-Auth-Request-Email header oauth2-proxy sets). Disabled unless every
    # setting below is explicitly provided; see app/auth.py.
    JWT_AUTH_ENABLED = os.environ.get('JWT_AUTH_ENABLED', 'false').lower() == 'true'
    JWT_ISSUER = os.environ.get('JWT_ISSUER')
    JWT_AUDIENCE = os.environ.get('JWT_AUDIENCE')
    JWT_JWKS_URL = os.environ.get('JWT_JWKS_URL')
    JWT_LEEWAY_SECONDS = 30


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    SQLALCHEMY_ECHO = True

    # Dev-only login bypass: current_user_email() falls back to this when
    # X-Auth-Request-Email is absent (no oauth2-proxy in front of local Docker).
    # Only defined here and in TestingConfig, never in Config/ProductionConfig,
    # so production has no such setting to read regardless of env vars.
    DEV_FAKE_USER_EMAIL = os.environ.get('DEV_FAKE_USER_EMAIL')


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False


class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    DATABASE_PATH = os.environ.get('DATABASE_PATH', 'data/test.db')
    SQLALCHEMY_DATABASE_URI = f'sqlite:///{DATABASE_PATH}'
    WTF_CSRF_ENABLED = False
    DEV_FAKE_USER_EMAIL = os.environ.get('DEV_FAKE_USER_EMAIL')


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
