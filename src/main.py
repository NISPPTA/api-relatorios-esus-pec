from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from src.modules.relatorios.router import router as relatorios_router

templates = Jinja2Templates(directory="templates")


def create_app() -> FastAPI:
    app = FastAPI(title="Painel Gerencial - Produção e-SUS PEC")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/", include_in_schema=False)
    async def root():
        return RedirectResponse(url="/busca")

    @app.get("/busca", include_in_schema=False)
    async def pagina_busca(request: Request):
        return templates.TemplateResponse("busca.html", {"request": request})

    @app.get("/relatorio/{id_profissional}", include_in_schema=False)
    async def pagina_relatorio(
        request: Request,
        id_profissional: int,
        nome: str = "Profissional",
        ano: int = 2026,
        mes_inicio: int = 5,
        mes_fim: int = 10,
        dias_desconto: int = 0,
    ):
        return templates.TemplateResponse(
            "relatorio.html",
            {
                "request": request,
                "id_profissional": id_profissional,
                "nome_profissional": nome,
                "filtro_ano": ano,
                "filtro_mes_inicio": mes_inicio,
                "filtro_mes_fim": mes_fim,
                "filtro_dias_desconto": dias_desconto,
            },
        )

    app.include_router(relatorios_router)
    return app


app = create_app()
