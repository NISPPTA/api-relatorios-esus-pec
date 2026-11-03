from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.modules.relatorios.router import router as relatorios_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="Painel Gerencial - Produção e-SUS PEC",
        description="API de consolidação e espelhamento de dados do Neon DB",
        version="1.0.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Em produção, substitua pelo domínio do frontend
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(relatorios_router)

    return app


app = create_app()
