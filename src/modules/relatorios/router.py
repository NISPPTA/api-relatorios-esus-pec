from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.database import get_db_session
from src.modules.relatorios.schemas import ProfissionalPerfil
from src.modules.relatorios.service import service

router = APIRouter(prefix="/api/relatorios", tags=["Relatórios de Produção"])
DbSession = Annotated[AsyncSession, Depends(get_db_session)]


@router.get(
    "/profissionais",
    summary="Listagem inteligente e paginada de profissionais",
)
async def api_listar_profissionais(
    q: str | None = Query(None, description="Filtrar por nome do profissional"),
    page: int = Query(1, ge=1, description="Número da página"),
    size: int = Query(10, ge=1, le=50, description="Tamanho da página"),
    session: DbSession = None,
):
    return await service.listar_profissionais(
        session, busca=q, pagina=page, tamanho=size
    )


@router.get(
    "/profissionais/{id_profissional}/perfil",
    response_model=ProfissionalPerfil,
    summary="Perfil e catálogo de relatórios de um profissional",
)
async def api_obter_perfil_profissional(
    id_profissional: int = Path(
        ..., description="ID numérico do profissional no e-SUS PEC"
    ),
    session: DbSession = None,
):
    perfil = await service.obter_perfil_profissional(session, id_profissional)
    if not perfil:
        raise HTTPException(
            status_code=404,
            detail="Profissional não encontrado ou sem histórico de produção associado.",
        )
    return perfil


@router.get(
    "/profissionais/{id_profissional}/matriz-producao",
    summary="Matriz Consolidada de Série Histórica",
    description="Retorna o relatório analítico idêntico à Série Histórica oficial do e-SUS PEC.",
)
async def api_matriz_producao(
    id_profissional: int = Path(..., description="ID do profissional"),
    ano: int = Query(..., description="Ano do relatório (ex: 2026)"),
    mes_inicio: int = Query(..., ge=1, le=12, description="Mês inicial numérico"),
    mes_fim: int = Query(..., ge=1, le=12, description="Mês final numérico"),
    session: DbSession = None,
):
    return await service.gerar_matriz_producao(
        session,
        id_profissional=id_profissional,
        ano=ano,
        mes_inicio=mes_inicio,
        mes_fim=mes_fim,
    )


@router.get(
    "/profissionais/{id_profissional}/visitas",
    summary="Boletim Analítico de Visitas Domiciliares (ACS/ACE)",
    description="Retorna os desfechos, os motivos das visitas e as métricas de busca ativa no território.",
)
async def api_relatorio_visitas(
    id_profissional: int = Path(..., description="ID numérico do profissional"),
    ano: int = Query(..., description="Ano do relatório"),
    mes_inicio: int = Query(..., ge=1, le=12, description="Mês inicial numérico"),
    mes_fim: int = Query(..., ge=1, le=12, description="Mês final numérico"),
    session: DbSession = None,
):
    return await service.gerar_relatorio_visitas(
        session,
        id_profissional=id_profissional,
        ano=ano,
        mes_inicio=mes_inicio,
        mes_fim=mes_fim,
    )


@router.get(
    "/profissionais/{id_profissional}/procedimentos",
    summary="Boletim de Procedimentos Ambulatoriais (SIGTAP)",
    description="Retorna o detalhamento de procedimentos e calcula a eficiência produtiva baseada em dias registados e dias úteis teóricos.",
)
async def api_relatorio_procedimentos(
    id_profissional: int = Path(..., description="ID numérico do profissional"),
    ano: int = Query(..., description="Ano do relatório"),
    mes_inicio: int = Query(..., ge=1, le=12, description="Mês inicial numérico"),
    mes_fim: int = Query(..., ge=1, le=12, description="Mês final numérico"),
    dias_desconto: int = Query(
        0, ge=0, description="Dias a descontar (férias, atestados, facultativos)"
    ),
    session: DbSession = None,
):
    return await service.gerar_relatorio_procedimentos(
        session,
        id_profissional=id_profissional,
        ano=ano,
        mes_inicio=mes_inicio,
        mes_fim=mes_fim,
        dias_desconto=dias_desconto,
    )
