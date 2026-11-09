import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from src.modules.relatorios.schemas import ProfissionalPerfil, RelatorioDisponivel
from src.modules.relatorios.service import service
from src.main import create_app


def perfil_sintetico() -> ProfissionalPerfil:
    return ProfissionalPerfil(
        id_profissional=12345,
        nome="Profissional Sintético",
        grupos=["MÉDICO"],
        frentes_atuacao=["Atendimento Individual"],
        relatorios_habilitados=[
            RelatorioDisponivel(
                id="consultas_medicas",
                titulo="Consultas Médicas",
                descricao="Relatório sintético para testes",
                categoria="Clínico",
                endpoint_relatorio=(
                    "/api/relatorios/profissionais/{id_profissional}/consultas-medicas"
                ),
            )
        ],
    )


def test_application_factory_registers_expected_routes() -> None:
    application = create_app()
    routes = {route.path for route in application.routes}

    assert application.title == "Painel Gerencial - Produção e-SUS PEC"
    assert "/" in routes
    assert "/busca" in routes
    assert "/dashboard/{id_profissional}" in routes
    assert "/api/relatorios/profissionais" in routes


def test_root_redirects_to_search_page(client: TestClient) -> None:
    response = client.get("/", follow_redirects=False)

    assert response.status_code == 307
    assert response.headers["location"] == "/busca"


@pytest.mark.parametrize(
    ("path", "expected_content"),
    [
        ("/busca", "Busca Dinâmica"),
        ("/dashboard/12345?nome=Profissional+Sintético", "Profissional Sintético"),
        (
            "/relatorio/12345?tipo=consultas_medicas&nome=Profissional+Sintético",
            "Consultas Médicas",
        ),
        (
            "/relatorio/12345?tipo=tipo_inexistente&nome=Profissional+Sintético",
            "fase seguinte",
        ),
    ],
)
def test_page_routes_render_templates(
    client: TestClient, path: str, expected_content: str
) -> None:
    response = client.get(path)

    assert response.status_code == 200
    assert expected_content in response.text


def test_list_professionals_returns_page_and_total(client: TestClient, monkeypatch):
    payload = {
        "total": 21,
        "pagina": 2,
        "tamanho": 10,
        "total_paginas": 3,
        "itens": [
            {
                "id_profissional": 12345,
                "nome": "Profissional Sintético",
                "grupos": ["MÉDICO"],
                "frentes_atuacao": ["Atendimento Individual"],
                "relatorios_habilitados": [],
            }
        ],
    }
    mock = AsyncMock(return_value=payload)
    monkeypatch.setattr(service, "listar_profissionais", mock)

    response = client.get(
        "/api/relatorios/profissionais?q=Sintético&page=2&size=10"
    )

    assert response.status_code == 200
    assert response.json() == payload
    mock.assert_awaited_once()
    assert mock.await_args.kwargs == {
        "busca": "Sintético",
        "pagina": 2,
        "tamanho": 10,
    }


def test_professional_service_applies_page_offset_without_database() -> None:
    rows = [
        {
            "id_profissional": 12345,
            "nome": "Profissional Sintético",
            "grupos_str": "MÉDICO",
            "frentes_str": "Atendimento Individual",
            "total_registros": 11,
        }
    ]
    result = SimpleNamespace(
        mappings=lambda: SimpleNamespace(all=lambda: rows)
    )
    session = SimpleNamespace(execute=AsyncMock(return_value=result))

    response = asyncio.run(
        service.listar_profissionais(
            session, busca="Sintético", pagina=2, tamanho=5
        )
    )

    assert response["total"] == 11
    assert response["pagina"] == 2
    assert response["tamanho"] == 5
    assert response["total_paginas"] == 3
    assert response["itens"][0]["id_profissional"] == 12345
    assert response["itens"][0]["grupos"] == ["MÉDICO"]
    parameters = session.execute.await_args.args[1]
    assert parameters == {
        "tamanho": 5,
        "offset": 5,
        "busca": "%Sintético%",
    }


def test_profile_endpoint_matches_pydantic_contract(
    client: TestClient, monkeypatch
) -> None:
    profile = perfil_sintetico()
    mock = AsyncMock(return_value=profile)
    monkeypatch.setattr(service, "obter_perfil_profissional", mock)

    response = client.get("/api/relatorios/profissionais/12345/perfil")

    assert response.status_code == 200
    assert response.json() == profile.model_dump(mode="json")
    mock.assert_awaited_once()


def test_missing_professional_returns_404(client: TestClient, monkeypatch) -> None:
    mock = AsyncMock(return_value=None)
    monkeypatch.setattr(service, "obter_perfil_profissional", mock)

    response = client.get("/api/relatorios/profissionais/99999/perfil")

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Profissional não encontrado ou sem histórico de produção associado."
    }


@pytest.mark.parametrize(
    ("path", "service_method", "expected_status"),
    [
        (
            "/api/relatorios/profissionais",
            "listar_profissionais",
            200,
        ),
        (
            "/api/relatorios/profissionais/12345/perfil",
            "obter_perfil_profissional",
            200,
        ),
        (
            "/api/relatorios/profissionais/12345/matriz-producao"
            "?ano=2026&mes_inicio=1&mes_fim=12",
            "gerar_matriz_producao",
            200,
        ),
        (
            "/api/relatorios/profissionais/12345/visitas"
            "?ano=2026&mes_inicio=1&mes_fim=12",
            "gerar_relatorio_visitas",
            200,
        ),
        (
            "/api/relatorios/profissionais/12345/procedimentos"
            "?ano=2026&mes_inicio=1&mes_fim=12",
            "gerar_relatorio_procedimentos",
            200,
        ),
        (
            "/api/relatorios/profissionais/12345/cadastros-territorio"
            "?ano=2026&mes_inicio=1&mes_fim=12",
            "gerar_relatorio_cadastros",
            200,
        ),
        (
            "/api/relatorios/profissionais/12345/relatorio-executivo"
            "?ano=2026&mes_inicio=1&mes_fim=12",
            "gerar_relatorio_executivo",
            200,
        ),
        (
            "/api/relatorios/profissionais/12345/consultas-odonto"
            "?ano=2026&mes_inicio=1&mes_fim=12",
            "gerar_relatorio_consultas_odonto",
            200,
        ),
        (
            "/api/relatorios/profissionais/12345/procedimentos-odonto"
            "?ano=2026&mes_inicio=1&mes_fim=12",
            "gerar_relatorio_procedimentos_odonto",
            200,
        ),
        (
            "/api/relatorios/profissionais/12345/lotacoes?ano=2026",
            "buscar_lotacoes_historicas_profissional",
            200,
        ),
    ],
)
def test_api_endpoint_returns_service_response(
    client: TestClient,
    monkeypatch,
    path: str,
    service_method: str,
    expected_status: int,
) -> None:
    if service_method == "obter_perfil_profissional":
        payload = perfil_sintetico()
    elif service_method == "listar_profissionais":
        payload = {
            "total": 0,
            "pagina": 1,
            "tamanho": 10,
            "total_paginas": 1,
            "itens": [],
        }
    else:
        payload = {"resultado": "sintético"}

    mock = AsyncMock(return_value=payload)
    monkeypatch.setattr(service, service_method, mock)

    response = client.get(path)

    assert response.status_code == expected_status
    mock.assert_awaited_once()


def test_medical_report_endpoint_aggregates_service_results(
    client: TestClient, monkeypatch
) -> None:
    responses = {
        "buscar_lotacao_principal_medico": {"nome": "Profissional Sintético"},
        "gerar_relatorio_consultas_medicas": {"resumo": {}, "top_ciap": []},
        "buscar_top_cids_medico": [],
        "calcular_taxa_sinais_vitais_medico": {"total_consultas": 0},
        "buscar_perfil_demografico_medico": {"total_atendimentos": 0},
        "calcular_absenteismo_agenda": {"resumo": {}},
        "buscar_top_procedimentos_avaliados_medico": [],
    }
    mocks = {}
    for method_name, payload in responses.items():
        mock = AsyncMock(return_value=payload)
        monkeypatch.setattr(service, method_name, mock)
        mocks[method_name] = mock

    response = client.get(
        "/api/relatorios/profissionais/12345/consultas-medicas"
        "?ano=2026&mes_inicio=1&mes_fim=12&cnes=1234567"
    )

    assert response.status_code == 200
    assert response.json() == {
        "periodo": {"ano": 2026, "mes_inicio": 1, "mes_fim": 12},
        "profissional": {"nome": "Profissional Sintético"},
        "producao_clinica": {},
        "morbidades": {"top_ciap_periodo": [], "top_cid_ano": []},
        "exame_fisico_sinais_vitais": {"total_consultas": 0},
        "perfil_demografico": {"total_atendimentos": 0},
        "gestao_agenda_absenteismo": {"resumo": {}},
        "procedimentos_e_exames_avaliados": [],
    }
    for mock in mocks.values():
        mock.assert_awaited_once()


@pytest.mark.parametrize(
    "query",
    [
        "?page=0",
        "?size=0",
        "?size=51",
    ],
)
def test_professional_list_rejects_invalid_pagination(
    client: TestClient, query: str
) -> None:
    response = client.get(f"/api/relatorios/profissionais{query}")

    assert response.status_code == 422


@pytest.mark.parametrize(
    "path",
    [
        "/api/relatorios/profissionais/12345/matriz-producao"
        "?ano=2019&mes_inicio=1&mes_fim=12",
        "/api/relatorios/profissionais/12345/matriz-producao"
        "?ano=2026&mes_inicio=0&mes_fim=12",
        "/api/relatorios/profissionais/12345/visitas"
        "?ano=2026&mes_inicio=1&mes_fim=13",
        "/api/relatorios/profissionais/nao-numerico/perfil",
    ],
)
def test_api_rejects_invalid_path_and_query_parameters(
    client: TestClient, path: str
) -> None:
    response = client.get(path)

    assert response.status_code == 422


def test_api_rejects_reversed_month_range(client: TestClient) -> None:
    response = client.get(
        "/api/relatorios/profissionais/12345/matriz-producao"
        "?ano=2026&mes_inicio=8&mes_fim=3"
    )

    assert response.status_code == 400
    assert "mês inicial" in response.json()["detail"]
