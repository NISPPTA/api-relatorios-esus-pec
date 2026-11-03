# Expõe o serviço ao mundo externo via API HTTP, injetando a sessão do banco.

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.database import get_db_session
from src.modules.relatorios.service import RelatorioProducaoService

router = APIRouter(prefix="/api/relatorios", tags=["Relatórios de Produção"])
service = RelatorioProducaoService()

# Injeção de Dependência Modernizada (Python 3.9+)
DbSession = Annotated[AsyncSession, Depends(get_db_session)]


@router.get(
    "/profissionais/{id_profissional}/matriz-producao",
    summary="Matriz Consolidada de Série Histórica",
)
async def api_matriz_producao(
    id_profissional: int,
    ano: int = Query(..., description="Ano do relatório"),
    mes_inicio: int = Query(..., ge=1, le=12, description="Mês inicial numérico"),
    mes_fim: int = Query(..., ge=1, le=12, description="Mês final numérico"),
    session: DbSession = None,
):
    """
    Retorna o relatório analítico idêntico à Série Histórica do e-SUS PEC,
    agregando produção por colunas mensais flexíveis.
    """
    if mes_inicio > mes_fim:
        raise HTTPException(
            status_code=400, detail="Mês inicial não pode ser superior ao mês final."
        )

    return await service.gerar_matriz_producao_mensal(
        session, id_profissional, ano, mes_inicio, mes_fim
    )
