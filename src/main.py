from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from src.modules.relatorios.router import router as relatorios_router

# Inicializa o Jinja2 apontando para a pasta templates
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
        return RedirectResponse(url="/docs")

    # Rota para renderizar a interface de busca
    @app.get("/busca", include_in_schema=False)
    async def pagina_busca(request: Request):
        return templates.TemplateResponse("busca.html", {"request": request})

    @app.get("/relatorio/{id_profissional}", include_in_schema=False)
    async def pagina_relatorio(
        request: Request, id_profissional: int, nome: str = "Profissional"
    ):
        """Renderiza o relatório final do profissional escolhido."""
        # Aqui, no futuro, você chamará a API para pegar os dados reais do banco
        # Por enquanto, renderizamos a casca passando as variáveis básicas para o Jinja2
        return templates.TemplateResponse(
            "relatorio.html",
            {
                "request": request,
                "id_profissional": id_profissional,
                "nome_profissional": nome,
            },
        )

    app.include_router(relatorios_router)

    return app


app = create_app()
