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
        tipo: str = "procedimentos_ambulatoriais",
        nome: str = "Profissional",
        ano: int = 2026,
        mes_inicio: int = 5,
        mes_fim: int = 10,
        dias_desconto: int = 0,
    ):
        # Mapeamento expandido para cobrir todos os 13 relatórios do catálogo
        templates_map = {
            # FASE 2: Concluídos
            "procedimentos_ambulatoriais": "relatorio_procedimentos.html",
            "visitas_domiciliares": "relatorio_visitas.html",
            "matriz_serie_historica": "relatorio_matriz.html",
            # FASE 3 e 4: Em Desenvolvimento (Mapeados para a página de contingência)
            "cadastros_territoriais": "relatorio_cadastros.html",
            "visitas_endemias": "em_construcao.html",
            "consultas_medicas": "em_construcao.html",
            "consultas_enfermagem": "em_construcao.html",
            "vacinacao_administrada": "em_construcao.html",
            "consultas_odontologicas": "em_construcao.html",
            "procedimentos_odonto": "em_construcao.html",
            "atendimentos_emulti": "em_construcao.html",
            "atividades_coletivas": "em_construcao.html",
            "cadastros_recepcao": "em_construcao.html",
        }

        # Fallback seguro: se o tipo não existir, mostra em construção
        template_escolhido = templates_map.get(tipo, "em_construcao.html")

        return templates.TemplateResponse(
            template_escolhido,
            {
                "request": request,
                "id_profissional": id_profissional,
                "nome_profissional": nome,
                "tipo_relatorio": tipo,
                "filtro_ano": ano,
                "filtro_mes_inicio": mes_inicio,
                "filtro_mes_fim": mes_fim,
                "filtro_dias_desconto": dias_desconto,
            },
        )

    app.include_router(relatorios_router)
    return app


app = create_app()
