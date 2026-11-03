from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.database import get_db
from src.modules.relatorios.schemas import ProfissionalPerfil
from src.modules.relatorios.service import service

router = APIRouter(prefix="/api/relatorios", tags=["Relatórios de Produção"])
DbSession = Annotated[AsyncSession, Depends(get_db)]


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
    summary="Perfil e catálogo de relatórios de um profissional específico",
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
            detail="Profissional não encontrado ou sem histórico de produção.",
        )
    return perfil


@router.get(
    "/profissionais/{id_profissional}/matriz-producao",
    summary="Matriz Consolidada de Série Histórica",
    description="Retorna o relatório analítico idêntico à Série Histórica do e-SUS PEC.",
)
async def api_matriz_producao(
    id_profissional: int = Path(..., description="ID do profissional"),
    ano: int = Query(..., description="Ano do relatório"),
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
