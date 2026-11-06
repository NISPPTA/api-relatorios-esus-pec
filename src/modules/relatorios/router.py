from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.database import get_db_session
from src.modules.relatorios.schemas import ProfissionalPerfil
from src.modules.relatorios.service import service

router = APIRouter(prefix="/api/relatorios", tags=["Relatórios de Produção"])
DbSession = Annotated[AsyncSession, Depends(get_db_session)]


def validar_intervalo_meses(mes_inicio: int, mes_fim: int) -> None:
    """Validação OWASP: Impede inversão temporal ou carga lógica inválida no banco."""
    if mes_inicio > mes_fim:
        raise HTTPException(
            status_code=400,
            detail="Validação falhou: O mês inicial não pode ser superior ao mês final.",
        )


@router.get(
    "/profissionais",
    summary="Listagem inteligente e paginada de profissionais",
)
async def api_listar_profissionais(
    session: DbSession,
    q: str | None = Query(None, description="Filtrar por nome do profissional"),
    page: int = Query(1, ge=1, description="Número da página"),
    size: int = Query(10, ge=1, le=50, description="Tamanho da página"),
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
    session: DbSession,
    id_profissional: int = Path(
        ..., description="ID numérico do profissional no e-SUS PEC"
    ),
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
)
async def api_matriz_producao(
    session: DbSession,
    id_profissional: int = Path(..., description="ID do profissional"),
    ano: int = Query(..., ge=2020, le=2030, description="Ano do relatório"),
    mes_inicio: int = Query(..., ge=1, le=12),
    mes_fim: int = Query(..., ge=1, le=12),
):
    validar_intervalo_meses(mes_inicio, mes_fim)
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
)
async def api_relatorio_visitas(
    session: DbSession,
    id_profissional: int = Path(..., description="ID numérico do profissional"),
    ano: int = Query(..., ge=2020, le=2030, description="Ano do relatório"),
    mes_inicio: int = Query(..., ge=1, le=12),
    mes_fim: int = Query(..., ge=1, le=12),
):
    validar_intervalo_meses(mes_inicio, mes_fim)
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
    description="Retorna detalhamento de procedimentos, evolução com dias úteis e distribuição diária.",
)
async def api_relatorio_procedimentos(
    session: DbSession,
    id_profissional: int = Path(..., description="ID numérico do profissional"),
    ano: int = Query(2026, ge=2020, le=2030, description="Ano da competência"),
    mes_inicio: int = Query(5, ge=1, le=12, description="Mês inicial numérico"),
    mes_fim: int = Query(10, ge=1, le=12, description="Mês final numérico"),
    dias_desconto: int = Query(
        0,
        ge=0,
        le=365,
        description="Dias a descontar (férias, atestados, facultativos)",
    ),
):
    validar_intervalo_meses(mes_inicio, mes_fim)
    return await service.gerar_relatorio_procedimentos(
        session,
        id_profissional=id_profissional,
        ano=ano,
        mes_inicio=mes_inicio,
        mes_fim=mes_fim,
        dias_desconto=dias_desconto,
    )


@router.get("/profissionais/{id_profissional}/cadastros-territorio")
async def relatorio_cadastros_territorio(
    session: DbSession,
    id_profissional: int = Path(..., description="ID numérico do profissional"),
    ano: int = Query(2026, ge=2020, le=2030),
    mes_inicio: int = Query(1, ge=1, le=12),
    mes_fim: int = Query(12, ge=1, le=12),
):
    validar_intervalo_meses(mes_inicio, mes_fim)
    return await service.gerar_relatorio_cadastros(
        session, id_profissional, ano, mes_inicio, mes_fim
    )


@router.get(
    "/profissionais/{id_profissional}/relatorio-executivo",
    summary="Painel Executivo: Auditoria e Conformidade Legal",
    description="Consolida Visitas, Matriz e Território, devolvendo um sistema de semáforos com base no Previne Brasil.",
)
async def api_relatorio_executivo(
    session: DbSession,
    id_profissional: int = Path(..., description="ID numérico do profissional"),
    ano: int = Query(2026, ge=2020, le=2030, description="Ano da competência"),
    mes_inicio: int = Query(1, ge=1, le=12, description="Mês inicial numérico"),
    mes_fim: int = Query(12, ge=1, le=12, description="Mês final numérico"),
):
    validar_intervalo_meses(mes_inicio, mes_fim)
    return await service.gerar_relatorio_executivo(
        session,
        id_profissional=id_profissional,
        ano=ano,
        mes_inicio=mes_inicio,
        mes_fim=mes_fim,
    )


@router.get("/profissionais/{id_profissional}/consultas-odonto")
async def obter_relatorio_consultas_odonto(
    session: DbSession,
    id_profissional: int = Path(..., description="ID numérico do profissional"),
    ano: int = Query(2026, ge=2020, le=2030),
    mes_inicio: int = Query(1, ge=1, le=12),
    mes_fim: int = Query(12, ge=1, le=12),
):
    """Retorna os dados consolidados de consultas e vigilância odontológica."""
    validar_intervalo_meses(mes_inicio, mes_fim)
    return await service.gerar_relatorio_consultas_odonto(
        session, id_profissional, ano, mes_inicio, mes_fim
    )


@router.get("/profissionais/{id_profissional}/procedimentos-odonto")
async def obter_relatorio_procedimentos_odonto(
    session: DbSession,
    id_profissional: int = Path(..., description="ID numérico do profissional"),
    ano: int = Query(2026, ge=2020, le=2030),
    mes_inicio: int = Query(1, ge=1, le=12),
    mes_fim: int = Query(12, ge=1, le=12),
):
    """Retorna o detalhamento categorizado dos procedimentos odontológicos executados."""
    validar_intervalo_meses(mes_inicio, mes_fim)
    return await service.gerar_relatorio_procedimentos_odonto(
        session, id_profissional, ano, mes_inicio, mes_fim
    )


@router.get(
    "/profissionais/{id_profissional}/lotacoes",
    summary="Lista Histórico de Lotações do Profissional no Ano",
)
async def api_lotacoes_profissional(
    session: DbSession,
    id_profissional: int = Path(..., description="ID numérico do profissional"),
    ano: int = Query(..., description="Ano do relatório"),
):
    return await service.buscar_lotacoes_historicas_profissional(
        session, id_profissional=id_profissional, ano=ano
    )


@router.get(
    "/profissionais/{id_profissional}/consultas-medicas",
    summary="Boletim Analítico de Consultas Médicas e Desempenho Clínico",
)
async def api_relatorio_consultas_medicas(
    session: DbSession,
    id_profissional: int = Path(
        ..., description="ID numérico do profissional no e-SUS PEC"
    ),
    ano: int = Query(2026, ge=2020, le=2030, description="Ano da competência"),
    mes_inicio: int = Query(1, ge=1, le=12, description="Mês inicial"),
    mes_fim: int = Query(12, ge=1, le=12, description="Mês final"),
    cnes: str | None = Query(
        None, description="Filtrar por unidade de saúde (Opcional)"
    ),
):
    validar_intervalo_meses(mes_inicio, mes_fim)

    lotacao = await service.buscar_lotacao_principal_medico(
        session=session,
        id_profissional=id_profissional,
        ano=ano,
        mes_inicio=mes_inicio,
        mes_fim=mes_fim,
        cnes=cnes,
    )
    consultas = await service.gerar_relatorio_consultas_medicas(
        session=session,
        id_profissional=id_profissional,
        ano=ano,
        mes_inicio=mes_inicio,
        mes_fim=mes_fim,
        cnes=cnes,
    )
    top_cids = await service.buscar_top_cids_medico(
        session=session,
        id_profissional=id_profissional,
        ano=ano,
        mes_inicio=mes_inicio,
        mes_fim=mes_fim,
        cnes=cnes,
    )
    sinais_vitais = await service.calcular_taxa_sinais_vitais_medico(
        session=session,
        id_profissional=id_profissional,
        ano=ano,
        mes_inicio=mes_inicio,
        mes_fim=mes_fim,
        cnes=cnes,
    )
    demografia = await service.buscar_perfil_demografico_medico(
        session=session,
        id_profissional=id_profissional,
        ano=ano,
        mes_inicio=mes_inicio,
        mes_fim=mes_fim,
        cnes=cnes,
    )
    absenteismo = await service.calcular_absenteismo_agenda(
        session=session,
        id_profissional=id_profissional,
        ano=ano,
        mes_inicio=mes_inicio,
        mes_fim=mes_fim,
        cnes=cnes,
    )
    procedimentos_avaliados = await service.buscar_top_procedimentos_avaliados_medico(
        session=session,
        id_profissional=id_profissional,
        ano=ano,
        mes_inicio=mes_inicio,
        mes_fim=mes_fim,
        limite=10,
        cnes=cnes,
    )

    return {
        "periodo": {"ano": ano, "mes_inicio": mes_inicio, "mes_fim": mes_fim},
        "profissional": lotacao,
        "producao_clinica": consultas.get("resumo", {}),
        "morbidades": {
            "top_ciap_periodo": consultas.get("top_ciap", []),
            "top_cid_ano": top_cids,
        },
        "exame_fisico_sinais_vitais": sinais_vitais,
        "perfil_demografico": demografia,
        "gestao_agenda_absenteismo": absenteismo,
        "procedimentos_e_exames_avaliados": procedimentos_avaliados,
    }
