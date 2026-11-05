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
)
async def api_matriz_producao(
    id_profissional: int = Path(..., description="ID do profissional"),
    ano: int = Query(..., description="Ano do relatório"),
    mes_inicio: int = Query(..., ge=1, le=12),
    mes_fim: int = Query(..., ge=1, le=12),
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
)
async def api_relatorio_visitas(
    id_profissional: int = Path(..., description="ID numérico do profissional"),
    ano: int = Query(..., description="Ano do relatório"),
    mes_inicio: int = Query(..., ge=1, le=12),
    mes_fim: int = Query(..., ge=1, le=12),
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
    description="Retorna detalhamento de procedimentos, evolução com dias úteis e distribuição diária.",
)
async def api_relatorio_procedimentos(
    id_profissional: int = Path(..., description="ID numérico do profissional"),
    ano: int = Query(2026, description="Ano da competência"),
    mes_inicio: int = Query(5, ge=1, le=12, description="Mês inicial numérico"),
    mes_fim: int = Query(10, ge=1, le=12, description="Mês final numérico"),
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


@router.get("/profissionais/{id_profissional}/cadastros-territorio")
async def relatorio_cadastros_territorio(
    id_profissional: int,
    ano: int = 2026,
    mes_inicio: int = 1,
    mes_fim: int = 12,
    session: DbSession = None,
):
    return await service.gerar_relatorio_cadastros(
        session, id_profissional, ano, mes_inicio, mes_fim
    )


@router.get(
    "/profissionais/{id_profissional}/relatorio-executivo",
    summary="Painel Executivo: Auditoria e Conformidade Legal",
    description="Consolida Visitas, Matriz e Território, devolvendo um sistema de semáforos com base no Previne Brasil.",
)
async def api_relatorio_executivo(
    id_profissional: int = Path(..., description="ID numérico do profissional"),
    ano: int = Query(2026, description="Ano da competência"),
    mes_inicio: int = Query(1, ge=1, le=12, description="Mês inicial numérico"),
    mes_fim: int = Query(12, ge=1, le=12, description="Mês final numérico"),
    session: DbSession = None,
):
    return await service.gerar_relatorio_executivo(
        session,
        id_profissional=id_profissional,
        ano=ano,
        mes_inicio=mes_inicio,
        mes_fim=mes_fim,
    )


@router.get("/profissionais/{id_profissional}/consultas-odonto")
async def obter_relatorio_consultas_odonto(
    id_profissional: int,
    ano: int = Query(2026, ge=2020, le=2030),
    mes_inicio: int = Query(1, ge=1, le=12),
    mes_fim: int = Query(12, ge=1, le=12),
    session: DbSession = None,
):
    """Retorna os dados consolidados de consultas e vigilância odontológica."""
    return await service.gerar_relatorio_consultas_odonto(
        session, id_profissional, ano, mes_inicio, mes_fim
    )


@router.get("/profissionais/{id_profissional}/procedimentos-odonto")
async def obter_relatorio_procedimentos_odonto(
    id_profissional: int,
    ano: int = Query(2026, ge=2020, le=2030),
    mes_inicio: int = Query(1, ge=1, le=12),
    mes_fim: int = Query(12, ge=1, le=12),
    session: DbSession = None,
):
    """Retorna o detalhamento categorizado dos procedimentos odontológicos executados."""
    return await service.gerar_relatorio_procedimentos_odonto(
        session, id_profissional, ano, mes_inicio, mes_fim
    )


@router.get(
    "/profissionais/{id_profissional}/consultas-medicas",
    summary="Boletim Analítico de Consultas Médicas e Desempenho Clínico",
    description=(
        "Consolida atendimentos, condutas clínicas, perfil demográfico, "
        "qualidade de exame físico (sinais vitais), morbidades (CIAP-2 e CID-10), "
        "procedimentos avaliados e absenteísmo auditado na agenda."
    ),
)
async def api_relatorio_consultas_medicas(
    id_profissional: int = Path(
        ..., description="ID numérico do profissional no e-SUS PEC"
    ),
    ano: int = Query(2026, ge=2020, le=2030, description="Ano da competência"),
    mes_inicio: int = Query(1, ge=1, le=12, description="Mês inicial"),
    mes_fim: int = Query(12, ge=1, le=12, description="Mês final"),
    session: DbSession = None,
):
    """
    Orquestra as 7 rotinas analíticas do módulo médico e entrega o
    payload completo para renderização do painel clínico e gerencial.
    """
    if mes_inicio > mes_fim:
        raise HTTPException(
            status_code=400,
            detail="O mês de início não pode ser superior ao mês final.",
        )

    # 1. Vínculo e Lotação Principal (UBS, Equipe, CNES, INE)
    lotacao = await service.buscar_lotacao_principal_medico(
        session=session, id_profissional=id_profissional, ano=ano
    )

    # 2. Resumo de Atendimentos, Condutas e Top CIAP-2
    consultas = await service.gerar_relatorio_consultas_medicas(
        session=session,
        id_profissional=id_profissional,
        ano=ano,
        mes_inicio=mes_inicio,
        mes_fim=mes_fim,
    )

    # 3. Top CIDs diagnosticados no ano
    top_cids = await service.buscar_top_cids_medico(
        session=session, id_profissional=id_profissional, ano=ano
    )

    # 4. Qualidade de Registro Clínico (PA e Peso no consultório)
    sinais_vitais = await service.calcular_taxa_sinais_vitais_medico(
        session=session, id_profissional=id_profissional, ano=ano
    )

    # 5. Pirâmide Etária, Divisão por Sexo e Gestantes
    demografia = await service.buscar_perfil_demografico_medico(
        session=session, id_profissional=id_profissional, ano=ano
    )

    # 6. Absenteísmo Auditado (Tratamento de faltas por inércia de agenda)
    absenteismo = await service.calcular_absenteismo_agenda(
        session=session, id_profissional=id_profissional, ano=ano
    )

    # 7. Procedimentos e Exames Clínicos Avaliados (ABEX / SIGTAP)
    procedimentos_avaliados = await service.buscar_top_procedimentos_avaliados_medico(
        session=session, id_profissional=id_profissional, ano=ano, limite=10
    )

    return {
        "periodo": {
            "ano": ano,
            "mes_inicio": mes_inicio,
            "mes_fim": mes_fim,
        },
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
