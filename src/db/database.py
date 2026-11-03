# Esta camada gerencia a sessão assíncrona utilizando as melhores práticas do SQLAlchemy 2.0.

from collections.abc import AsyncGenerator

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


class Settings(BaseSettings):
    # O Pydantic buscará automaticamente a DATABASE_URL no arquivo .env
    DATABASE_URL: str
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()

# Criação da engine assíncrona (O Neon funciona perfeitamente com asyncpg)
engine = create_async_engine(settings.DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False)


async def get_db_session() -> AsyncGenerator[AsyncSession]:
    """Injeção de dependência para instanciar a conexão em cada requisição."""
    async with AsyncSessionLocal() as session:
        yield session
