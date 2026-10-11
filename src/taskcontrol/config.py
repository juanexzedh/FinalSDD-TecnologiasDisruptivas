import os


class Config:
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///taskcontrol.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    WTF_CSRF_ENABLED = True
    REQUIRE_SECRET_KEY = True

    @staticmethod
    def secret_key():
        return os.environ.get("SECRET_KEY")


class DevelopmentConfig(Config):
    pass


class ProductionConfig(Config):
    SESSION_COOKIE_SECURE = True


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SECRET_KEY = "clave-solo-para-pruebas"  # nunca se usa fuera de Testing
    WTF_CSRF_ENABLED = False
    REQUIRE_SECRET_KEY = False


CONFIGS = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
}
