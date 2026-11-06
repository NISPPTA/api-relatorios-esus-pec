import calendar
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.relatorios.schemas import ProfissionalPerfil, RelatorioDisponivel

# Catálogo mestre de relatórios do sistema
CATALOGO_RELATORIOS: dict[str, RelatorioDisponivel] = {
    "matriz_serie_historica": RelatorioDisponivel(
        id="matriz_serie_historica",
        titulo="Matriz Consolidada de Série Histórica",
        descricao="Série temporal oficial com pivoteamento mensal das 12 categorias e-SUS PEC",
        categoria="Consolidado",
        endpoint_relatorio="/api/relatorios/profissionais/{id_profissional}/matriz-producao",
    ),
    "visitas_domiciliares": RelatorioDisponivel(
        id="visitas_domiciliares",
        titulo="Boletim Analítico de Visitas Domiciliares",
        descricao="Desfechos de visitas, motivos, recusas e busca ativa no território",
        categoria="Territorial",
        endpoint_relatorio="/api/relatorios/profissionais/{id_profissional}/visitas",
    ),
    "cadastros_territoriais": RelatorioDisponivel(
        id="cadastros_territoriais",
        titulo="Acompanhamento Territorial e Cadastros",
        descricao="Famílias e cidadãos adscritos, atualizações e condições do território",
        categoria="Territorial",
        endpoint_relatorio="/api/relatorios/profissionais/{id_profissional}/cadastros-territorio",
    ),
    "visitas_endemias": RelatorioDisponivel(
        id="visitas_endemias",
        titulo="Boletim de Controle Vetorial e Endemias",
        descricao="Ações de campo, imóveis inspecionados e tratamentos focais",
        categoria="Vigilância",
        endpoint_relatorio="/api/relatorios/profissionais/{id_profissional}/endemias",
    ),
    "consultas_medicas": RelatorioDisponivel(
        id="consultas_medicas",
        titulo="Consultas Médicas e Problemas Avaliados",
        descricao="Atendimentos clínicos, morbidades CIAP-2 e CID-10 e encaminhamentos",
        categoria="Clínico",
        endpoint_relatorio="/api/relatorios/profissionais/{id_profissional}/consultas-medicas",
    ),
    "consultas_enfermagem": RelatorioDisponivel(
        id="consultas_enfermagem",
        titulo="Consultas de Enfermagem e Linhas de Cuidado",
        descricao="Acompanhamento de pré-natal, puericultura, citopatológico e hipertensos",
        categoria="Clínico",
        endpoint_relatorio="/api/relatorios/profissionais/{id_profissional}/consultas-enfermagem",
    ),
    "procedimentos_ambulatoriais": RelatorioDisponivel(
        id="procedimentos_ambulatoriais",
        titulo="Boletim de Procedimentos Clínicos",
        descricao="Detalhamento individual de procedimentos realizados por código SIGTAP",
        categoria="Procedimentos",
        endpoint_relatorio="/api/relatorios/profissionais/{id_profissional}/procedimentos",
    ),
    "vacinacao_administrada": RelatorioDisponivel(
        id="vacinacao_administrada",
        titulo="Registro de Doses e Imunobiológicos",
        descricao="Estatísticas de vacinas administradas por lote, imunobiológico e faixa etária",
        categoria="Imunização",
        endpoint_relatorio="/api/relatorios/profissionais/{id_profissional}/vacinacao",
    ),
    "consultas_odontologicas": RelatorioDisponivel(
        id="consultas_odontologicas",
        titulo="Consultas e Tratamentos Odontológicos",
        descricao="Primeiras consultas programáticas, tratamentos concluídos e urgências bucais",
        categoria="Saúde Bucal",
        endpoint_relatorio="/api/relatorios/profissionais/{id_profissional}/consultas-odonto",
    ),
    "procedimentos_odonto": RelatorioDisponivel(
        id="procedimentos_odonto",
        titulo="Procedimentos Odontológicos Especializados",
        descricao="Exodontias, restaurações, profilaxias e procedimentos coletivos bucais",
        categoria="Saúde Bucal",
        endpoint_relatorio="/api/relatorios/profissionais/{id_profissional}/procedimentos-odonto",
    ),
    "atendimentos_emulti": RelatorioDisponivel(
        id="atendimentos_emulti",
        titulo="Atendimentos Especializados Multiprofissionais",
        descricao="Produção assistencial das equipes eMulti (Psicologia, Fisioterapia, Nutrição, etc.)",
        categoria="eMulti",
        endpoint_relatorio="/api/relatorios/profissionais/{id_profissional}/atendimentos-emulti",
    ),
    "atividades_coletivas": RelatorioDisponivel(
        id="atividades_coletivas",
        titulo="Atividades Coletivas e Promoção da Saúde",
        descricao="Ações educativas em grupo, reuniões de equipe e atendimentos coletivos",
        categoria="Coletivo",
        endpoint_relatorio="/api/relatorios/profissionais/{id_profissional}/atividades-coletivas",
    ),
    "cadastros_recepcao": RelatorioDisponivel(
        id="cadastros_recepcao",
        titulo="Fluxo de Cadastros e Acolhimento",
        descricao="Novos cadastros individuais e domiciliares e atualizações na recepção",
        categoria="Administrativo",
        endpoint_relatorio="/api/relatorios/profissionais/{id_profissional}/cadastros-recepcao",
    ),
    "relatorio_executivo": RelatorioDisponivel(
        id="relatorio_executivo",
        titulo="Painel Executivo de Conformidade e Desempenho",
        descricao="Auditoria automatizada cruzando visitas, território e regras do Ministério da Saúde",
        categoria="Gestão e Conformidade",
        endpoint_relatorio="/api/relatorios/profissionais/{id_profissional}/relatorio-executivo",
    ),
}

MAPEAMENTO_GRUPOS: dict[str, list[str]] = {
    "ACS - AGENTE COMUNITÁRIO DE SAÚDE": [
        "relatorio_executivo",
        "visitas_domiciliares",
        "cadastros_territoriais",
    ],
    "ACE - AGENTE DE COMBATE ÀS ENDEMIAS": ["visitas_endemias"],
    "MÉDICO": ["consultas_medicas", "procedimentos_ambulatoriais"],
    "ENFERMEIRO": [
        "consultas_enfermagem",
        "procedimentos_ambulatoriais",
        "vacinacao_administrada",
    ],
    "AUXILIAR OU TÉCNICO DE ENFERMAGEM": [
        "procedimentos_ambulatoriais",
        "vacinacao_administrada",
    ],
    "CIRURGIÃO DENTISTA": ["consultas_odontologicas", "procedimentos_odonto"],
    "ASB - AUXILIAR DE SAÚDE BUCAL": ["procedimentos_odonto"],
    "TSB - TÉCNICO DE SAÚDE BUCAL": ["procedimentos_odonto"],
    "OUTRO PROF. NÍVEL SUPERIOR": [
        "atendimentos_emulti",
        "atividades_coletivas",
        "procedimentos_ambulatoriais",
    ],
    "OUTRO PROF. NÍVEL MÉDIO/TÉCNICO": ["procedimentos_ambulatoriais"],
    "ADMINISTRATIVO / RECEPÇÃO": ["cadastros_recepcao"],
    "DIGITADOR": ["cadastros_recepcao"],
}


class RelatoriosService:
    def _resolver_relatorios_para_grupos(
        self, grupos: list[str]
    ) -> list[RelatorioDisponivel]:
        chaves_resolvidas = {"matriz_serie_historica"}
        for grupo in grupos:
            chaves = MAPEAMENTO_GRUPOS.get(grupo, [])
            chaves_resolvidas.update(chaves)

        return [
            CATALOGO_RELATORIOS[chave]
            for chave in chaves_resolvidas
            if chave in CATALOGO_RELATORIOS
        ]

    def _obter_metricas_calendario_mes(self, ano: int, mes: int) -> tuple[int, int]:
        """Retorna (dias_totais_no_mes, dias_uteis_seg_a_sex)."""
        _, total_dias = calendar.monthrange(ano, mes)
        matriz_semanas = calendar.monthcalendar(ano, mes)
        dias_uteis = sum(
            sum(1 for dia in semana[:5] if dia != 0) for semana in matriz_semanas
        )
        return total_dias, dias_uteis

    async def listar_profissionais(
        self,
        session: AsyncSession,
        busca: str | None = None,
        pagina: int = 1,
        tamanho: int = 10,
    ) -> dict[str, Any]:
        """Consulta paginada de profissionais inteligente com offset e limit."""
        filtro_sql = "AND UPPER(p.nome) LIKE UPPER(:busca)" if busca else ""
        offset = (pagina - 1) * tamanho

        sql = f"""
            WITH producao_cbo AS (
                SELECT co_dim_profissional AS id_prof, co_dim_cbo AS id_cbo, 'Procedimento' AS origem FROM tb_fat_proced_atend
                UNION SELECT co_dim_profissional, co_dim_cbo, 'Visita Domiciliar' FROM tb_fat_visita_domiciliar
                UNION SELECT co_dim_profissional_1, co_dim_cbo_1, 'Atendimento Individual' FROM tb_fat_atendimento_individual
                UNION SELECT co_dim_profissional_1, co_dim_cbo_1, 'Atendimento Odonto' FROM tb_fat_atendimento_odonto
                UNION SELECT co_dim_profissional, co_dim_cbo, 'Cadastro' FROM tb_fat_cad_individual
            ),
            classificacao_base AS (
                SELECT 
                    p.co_seq_dim_profissional AS id_profissional,
                    p.no_profissional AS nome,
                    COALESCE(
                        g.ds_grupo_cbo, 
                        CASE 
                            WHEN c.nu_cbo IN ('411010', '422105') THEN 'ADMINISTRATIVO / RECEPÇÃO' 
                            WHEN c.nu_cbo = '412110' THEN 'DIGITADOR' 
                            ELSE 'OUTROS' 
                        END
                    ) AS grupo_ajustado,
                    pc.origem
                FROM producao_cbo pc
                JOIN tb_dim_profissional p ON p.co_seq_dim_profissional = pc.id_prof
                LEFT JOIN tb_dim_cbo c ON c.co_seq_dim_cbo = pc.id_cbo
                LEFT JOIN tb_dim_grupo_cbo g ON g.co_dim_cbo = c.co_seq_dim_cbo
                WHERE p.co_seq_dim_profissional <> 1
            )
            SELECT 
                id_profissional, 
                nome,
                ARRAY_TO_STRING(ARRAY_AGG(DISTINCT grupo_ajustado ORDER BY grupo_ajustado), ' | ') AS grupos_str,
                ARRAY_TO_STRING(ARRAY_AGG(DISTINCT origem ORDER BY origem), ', ') AS frentes_str,
                COUNT(*) OVER() AS total_registros
            FROM classificacao_base p
            WHERE 1=1 {filtro_sql}
            GROUP BY id_profissional, nome
            ORDER BY nome ASC
            LIMIT :tamanho OFFSET :offset;
        """

        parametros = {"tamanho": tamanho, "offset": offset}
        if busca:
            parametros["busca"] = f"%{busca}%"

        result = await session.execute(text(sql), parametros)
        linhas = result.mappings().all()

        profissionais = []
        total = linhas[0]["total_registros"] if linhas else 0

        for linha in linhas:
            grupos = (
                [g.strip() for g in linha["grupos_str"].split("|")]
                if linha["grupos_str"]
                else []
            )
            frentes = (
                [f.strip() for f in linha["frentes_str"].split(",")]
                if linha["frentes_str"]
                else []
            )

            profissionais.append(
                {
                    "id_profissional": linha["id_profissional"],
                    "nome": linha["nome"],
                    "grupos": grupos,
                    "frentes_atuacao": frentes,
                    "relatorios_habilitados": self._resolver_relatorios_para_grupos(
                        grupos
                    ),
                }
            )

        return {
            "total": total,
            "pagina": pagina,
            "tamanho": tamanho,
            "total_paginas": (total + tamanho - 1) // tamanho if total > 0 else 1,
            "itens": profissionais,
        }

    async def obter_perfil_profissional(
        self, session: AsyncSession, id_profissional: int
    ) -> ProfissionalPerfil | None:
        sql = """
            WITH producao_cbo AS (
                SELECT co_dim_profissional AS id_prof, co_dim_cbo AS id_cbo, 'Procedimento' AS origem FROM tb_fat_proced_atend
                UNION SELECT co_dim_profissional, co_dim_cbo, 'Visita Domiciliar' FROM tb_fat_visita_domiciliar
                UNION SELECT co_dim_profissional_1, co_dim_cbo_1, 'Atendimento Individual' FROM tb_fat_atendimento_individual
                UNION SELECT co_dim_profissional_1, co_dim_cbo_1, 'Atendimento Odonto' FROM tb_fat_atendimento_odonto
                UNION SELECT co_dim_profissional, co_dim_cbo, 'Cadastro' FROM tb_fat_cad_individual
            ),
            classificacao_base AS (
                SELECT 
                    p.co_seq_dim_profissional AS id_profissional,
                    p.no_profissional AS nome,
                    COALESCE(
                        g.ds_grupo_cbo,
                        CASE 
                            WHEN c.nu_cbo IN ('411010', '422105') THEN 'ADMINISTRATIVO / RECEPÇÃO'
                            WHEN c.nu_cbo = '412110' THEN 'DIGITADOR'
                            ELSE 'OUTROS'
                        END
                    ) AS grupo_ajustado,
                    pc.origem
                FROM producao_cbo pc
                JOIN tb_dim_profissional p ON p.co_seq_dim_profissional = pc.id_prof
                LEFT JOIN tb_dim_cbo c ON c.co_seq_dim_cbo = pc.id_cbo
                LEFT JOIN tb_dim_grupo_cbo g ON g.co_dim_cbo = c.co_seq_dim_cbo
                WHERE p.co_seq_dim_profissional = :id_prof
            )
            SELECT 
                id_profissional,
                nome,
                ARRAY_TO_STRING(ARRAY_AGG(DISTINCT grupo_ajustado ORDER BY grupo_ajustado), ' | ') AS grupos_str,
                ARRAY_TO_STRING(ARRAY_AGG(DISTINCT origem ORDER BY origem), ', ') AS frentes_str
            FROM classificacao_base
            GROUP BY id_profissional, nome;
        """

        result = await session.execute(text(sql), {"id_prof": id_profissional})
        linha = result.mappings().first()
        if not linha:
            return None

        grupos = (
            [g.strip() for g in linha["grupos_str"].split("|")]
            if linha["grupos_str"]
            else []
        )
        frentes = (
            [f.strip() for f in linha["frentes_str"].split(",")]
            if linha["frentes_str"]
            else []
        )

        return ProfissionalPerfil(
            id_profissional=linha["id_profissional"],
            nome=linha["nome"],
            grupos=grupos,
            frentes_atuacao=frentes,
            relatorios_habilitados=self._resolver_relatorios_para_grupos(grupos),
        )

    async def gerar_matriz_producao(
        self,
        session: AsyncSession,
        id_profissional: int,
        ano: int,
        mes_inicio: int,
        mes_fim: int,
    ) -> dict[str, Any]:
        meses_nomes = {
            1: "jan",
            2: "fev",
            3: "mar",
            4: "abr",
            5: "mai",
            6: "jun",
            7: "jul",
            8: "ago",
            9: "set",
            10: "out",
            11: "nov",
            12: "dez",
        }
        meses_selecionados = [meses_nomes[m] for m in range(mes_inicio, mes_fim + 1)]

        sql_prof = text(
            "SELECT no_profissional FROM tb_dim_profissional WHERE co_seq_dim_profissional = :id"
        )
        res_prof = await session.execute(sql_prof, {"id": id_profissional})
        row_prof = res_prof.first()
        nome_profissional = row_prof[0] if row_prof else "Desconhecido"

        colunas_soma = ", ".join(
            [f'COALESCE(SUM("{m}"), 0) AS "{m}"' for m in meses_selecionados]
        )

        query = f"""
            WITH dim_tempo_filtrada AS (
                SELECT co_seq_dim_tempo, nu_mes
                FROM tb_dim_tempo
                WHERE nu_ano = :ano AND nu_mes BETWEEN :mes_inicio AND :mes_fim
            ),
            producao_base AS (
                SELECT f.co_dim_profissional AS id_prof, t.nu_mes, 'Procedimentos' AS categoria FROM tb_fat_proced_atend f JOIN dim_tempo_filtrada t ON t.co_seq_dim_tempo = f.co_dim_tempo WHERE f.co_dim_profissional = :id_prof
                UNION ALL SELECT f.co_dim_profissional, t.nu_mes, 'Visita Domiciliar' FROM tb_fat_visita_domiciliar f JOIN dim_tempo_filtrada t ON t.co_seq_dim_tempo = f.co_dim_tempo WHERE f.co_dim_profissional = :id_prof
                UNION ALL SELECT f.co_dim_profissional_1, t.nu_mes, 'Atendimento Individual' FROM tb_fat_atendimento_individual f JOIN dim_tempo_filtrada t ON t.co_seq_dim_tempo = f.co_dim_tempo WHERE f.co_dim_profissional_1 = :id_prof
                UNION ALL SELECT f.co_dim_profissional_1, t.nu_mes, 'Atendimento Odontológico' FROM tb_fat_atendimento_odonto f JOIN dim_tempo_filtrada t ON t.co_seq_dim_tempo = f.co_dim_tempo WHERE f.co_dim_profissional_1 = :id_prof
                UNION ALL SELECT f.co_dim_profissional_1, t.nu_mes, 'Atendimento Domiciliar' FROM tb_fat_atendimento_domiciliar f JOIN dim_tempo_filtrada t ON t.co_seq_dim_tempo = f.co_dim_tempo WHERE f.co_dim_profissional_1 = :id_prof
                UNION ALL SELECT f.co_dim_profissional, t.nu_mes, 'Cadastro Individual' FROM tb_fat_cad_individual f JOIN dim_tempo_filtrada t ON t.co_seq_dim_tempo = f.co_dim_tempo WHERE f.co_dim_profissional = :id_prof
                UNION ALL SELECT f.co_dim_profissional, t.nu_mes, 'Cadastro Domiciliar' FROM tb_fat_cad_domiciliar f JOIN dim_tempo_filtrada t ON t.co_seq_dim_tempo = f.co_dim_tempo WHERE f.co_dim_profissional = :id_prof
                UNION ALL SELECT f.co_dim_profissional, t.nu_mes, 'Vacinação' FROM tb_fat_vacinacao f JOIN dim_tempo_filtrada t ON t.co_seq_dim_tempo = f.co_dim_tempo WHERE f.co_dim_profissional = :id_prof
                UNION ALL SELECT f.co_dim_profissional, t.nu_mes, 'Atividade Coletiva' FROM tb_fat_atividade_coletiva f JOIN dim_tempo_filtrada t ON t.co_seq_dim_tempo = f.co_dim_tempo WHERE f.co_dim_profissional = :id_prof
                UNION ALL SELECT f.co_dim_profissional, t.nu_mes, 'Consumo Alimentar' FROM tb_fat_marca_consumo_alimnt f JOIN dim_tempo_filtrada t ON t.co_seq_dim_tempo = f.co_dim_tempo WHERE f.co_dim_profissional = :id_prof
                UNION ALL SELECT f.co_dim_profissional_1, t.nu_mes, 'Avaliação de Elegibilidade' FROM tb_fat_avaliacao_elegibilidade f JOIN dim_tempo_filtrada t ON t.co_seq_dim_tempo = f.co_dim_tempo WHERE f.co_dim_profissional_1 = :id_prof
            ),
            pivoteado AS (
                SELECT 
                    categoria,
                    COUNT(CASE WHEN nu_mes = 1 THEN 1 END) AS "jan", COUNT(CASE WHEN nu_mes = 2 THEN 1 END) AS "fev",
                    COUNT(CASE WHEN nu_mes = 3 THEN 1 END) AS "mar", COUNT(CASE WHEN nu_mes = 4 THEN 1 END) AS "abr",
                    COUNT(CASE WHEN nu_mes = 5 THEN 1 END) AS "mai", COUNT(CASE WHEN nu_mes = 6 THEN 1 END) AS "jun",
                    COUNT(CASE WHEN nu_mes = 7 THEN 1 END) AS "jul", COUNT(CASE WHEN nu_mes = 8 THEN 1 END) AS "ago",
                    COUNT(CASE WHEN nu_mes = 9 THEN 1 END) AS "set", COUNT(CASE WHEN nu_mes = 10 THEN 1 END) AS "out",
                    COUNT(CASE WHEN nu_mes = 11 THEN 1 END) AS "nov", COUNT(CASE WHEN nu_mes = 12 THEN 1 END) AS "dez"
                FROM producao_base
                GROUP BY categoria
            ),
            categorias_oficiais AS (
                SELECT unnest(ARRAY[
                    'Cadastro Individual', 'Cadastro Domiciliar', 'Atendimento Individual',
                    'Atendimento Odontológico', 'Procedimentos', 'Visita Domiciliar',
                    'Atividade Coletiva', 'Consumo Alimentar', 'Atendimento Domiciliar',
                    'Avaliação de Elegibilidade', 'Vacinação'
                ]) AS categoria
            )
            SELECT c.categoria, {colunas_soma}
            FROM categorias_oficiais c
            LEFT JOIN pivoteado p ON p.categoria = c.categoria
            GROUP BY c.categoria ORDER BY c.categoria;
        """

        result = await session.execute(
            text(query),
            {
                "id_prof": id_profissional,
                "ano": ano,
                "mes_inicio": mes_inicio,
                "mes_fim": mes_fim,
            },
        )
        linhas = result.mappings().all()

        dados_matriz = []
        totais_colunas = {m: 0 for m in meses_selecionados}
        total_geral = 0

        for r in linhas:
            item = {"categoria": r["categoria"]}
            soma_linha = 0
            for m in meses_selecionados:
                v = int(r[m] or 0)
                item[m] = v
                totais_colunas[m] += v
                soma_linha += v
            item["total"] = soma_linha
            total_geral += soma_linha
            dados_matriz.append(item)

        linha_total = {"categoria": "Total Geral"}
        linha_total.update(totais_colunas)
        linha_total["total"] = total_geral

        return {
            "profissional": {"id": id_profissional, "nome": nome_profissional},
            "periodo": {"ano": ano, "mes_inicio": mes_inicio, "mes_fim": mes_fim},
            "colunas": meses_selecionados + ["total"],
            "matriz": dados_matriz,
            "resumo": linha_total,
        }

    async def gerar_relatorio_visitas(
        self,
        session: AsyncSession,
        id_profissional: int,
        ano: int,
        mes_inicio: int,
        mes_fim: int,
    ) -> dict[str, Any]:
        sql_desfecho = """
            SELECT d.ds_desfecho_visita AS desfecho, COUNT(1) AS total
            FROM tb_fat_visita_domiciliar f
            JOIN tb_dim_tempo t ON t.co_seq_dim_tempo = f.co_dim_tempo
            JOIN tb_dim_desfecho_visita d ON d.co_seq_dim_desfecho_visita = f.co_dim_desfecho_visita
            WHERE f.co_dim_profissional = :id_prof
              AND t.nu_ano = :ano AND t.nu_mes BETWEEN :mes_inicio AND :mes_fim
            GROUP BY d.ds_desfecho_visita
            ORDER BY total DESC;
        """

        sql_motivos = """
            SELECT 
                -- Motivos da Visita
                COALESCE(SUM(f.st_mot_vis_cad_att), 0) AS mot_vis_cad_att,
                COALESCE(SUM(f.st_mot_vis_visita_periodica), 0) AS mot_vis_visita_periodica,
                COALESCE(SUM(f.st_mot_vis_busca_ativa), 0) AS mot_vis_busca_ativa,
                COALESCE(SUM(f.st_mot_vis_acompanhamento), 0) AS mot_vis_acompanhamento,
                COALESCE(SUM(f.st_mot_vis_convte_atvidd_cltva), 0) AS mot_vis_convte_atvidd_cltva,
                COALESCE(SUM(f.st_mot_vis_orintacao_prevncao), 0) AS mot_vis_orintacao_prevncao,
                COALESCE(SUM(f.st_mot_vis_egresso_internacao), 0) AS mot_vis_egresso_internacao,
                COALESCE(SUM(f.st_mot_vis_ctrl_ambnte_vetor), 0) AS mot_vis_ctrl_ambnte_vetor,
                COALESCE(SUM(f.st_mot_vis_outros), 0) AS mot_vis_outros,

                -- Buscas Ativas
                COALESCE(SUM(f.st_busca_ativa_consulta), 0) AS busca_ativa_consulta,
                COALESCE(SUM(f.st_busca_ativa_exame), 0) AS busca_ativa_exame,
                COALESCE(SUM(f.st_busca_ativa_vacina), 0) AS busca_ativa_vacina,
                COALESCE(SUM(f.st_busca_ativa_bolsa_familia), 0) AS busca_ativa_bolsa_familia,

                -- Ciclos de Vida
                COALESCE(SUM(f.st_acomp_gestante), 0) AS acomp_gestante,
                COALESCE(SUM(f.st_acomp_puerpera), 0) AS acomp_puerpera,
                COALESCE(SUM(f.st_acomp_recem_nascido), 0) AS acomp_recem_nascido,
                COALESCE(SUM(f.st_acomp_crianca), 0) AS acomp_crianca,
                COALESCE(SUM(f.st_acomp_pessoa_idosa), 0) AS acomp_pessoa_idosa,

                -- Condições Clínicas
                COALESCE(SUM(f.st_acomp_pessoa_hipertensao), 0) AS acomp_pessoa_hipertensao,
                COALESCE(SUM(f.st_acomp_pessoa_diabetes), 0) AS acomp_pessoa_diabetes,
                COALESCE(SUM(f.st_acomp_pessoa_asma), 0) AS acomp_pessoa_asma,
                COALESCE(SUM(f.st_acomp_pessoa_dpoc_enfisema), 0) AS acomp_pessoa_dpoc_enfisema,
                COALESCE(SUM(f.st_acomp_pessoa_cancer), 0) AS acomp_pessoa_cancer,
                COALESCE(SUM(f.st_acomp_pessoa_doenca_cronica), 0) AS acomp_pessoa_doenca_cronica,
                COALESCE(SUM(f.st_acomp_pessoa_hanseniase), 0) AS acomp_pessoa_hanseniase,
                COALESCE(SUM(f.st_acomp_pessoa_tuberculose), 0) AS acomp_pessoa_tuberculose,
                COALESCE(SUM(f.st_acomp_sintomaticos_respirat), 0) AS acomp_sintomaticos_respirat,

                -- Vulnerabilidades e Condição Social
                COALESCE(SUM(f.st_acomp_tabagista), 0) AS acomp_tabagista,
                COALESCE(SUM(f.st_acomp_usuario_alcool), 0) AS acomp_usuario_alcool,
                COALESCE(SUM(f.st_acomp_usuario_outras_drogra), 0) AS acomp_usuario_outras_drogra,
                COALESCE(SUM(f.st_acomp_saude_mental), 0) AS acomp_saude_mental,
                COALESCE(SUM(f.st_acomp_pessoa_desnutricao), 0) AS acomp_pessoa_desnutricao,
                COALESCE(SUM(f.st_acomp_pessoa_reabil_deficie), 0) AS acomp_pessoa_reabil_deficie,
                COALESCE(SUM(f.st_acomp_domiciliados_acamados), 0) AS acomp_domiciliados_acamados,
                COALESCE(SUM(f.st_acomp_condi_vulnerab_social), 0) AS acomp_condi_vulnerab_social,
                COALESCE(SUM(f.st_acomp_condi_bolsa_familia), 0) AS acomp_condi_bolsa_familia,

                -- Ações de Vigilância e Endemias
                COALESCE(SUM(f.st_ctrl_amb_vet_imovel_foco), 0) AS ctrl_amb_vet_imovel_foco,
                COALESCE(SUM(f.st_ctrl_amb_vet_tratamnt_focal), 0) AS ctrl_amb_vet_tratamnt_focal,
                COALESCE(SUM(f.st_ctrl_amb_vet_acao_educativa), 0) AS ctrl_amb_vet_acao_educativa,
                COALESCE(SUM(f.st_ctrl_amb_vet_acao_mecanica), 0) AS ctrl_amb_vet_acao_mecanica,

                -- Operacional
                COALESCE(SUM(f.st_visita_compartilhada), 0) AS visita_compartilhada
            FROM tb_fat_visita_domiciliar f
            JOIN tb_dim_tempo t ON t.co_seq_dim_tempo = f.co_dim_tempo
            WHERE f.co_dim_profissional = :id_prof
              AND t.nu_ano = :ano AND t.nu_mes BETWEEN :mes_inicio AND :mes_fim;
        """

        parametros = {
            "id_prof": id_profissional,
            "ano": ano,
            "mes_inicio": mes_inicio,
            "mes_fim": mes_fim,
        }
        res_desfechos = await session.execute(text(sql_desfecho), parametros)
        res_motivos = await session.execute(text(sql_motivos), parametros)

        linhas_desfechos = res_desfechos.mappings().all()
        linha_motivo = res_motivos.mappings().first()

        dados_desfechos = [
            {"desfecho": r["desfecho"], "total": r["total"]} for r in linhas_desfechos
        ]
        total_visitas = sum(r["total"] for r in dados_desfechos)
        motivos = {k: int(v) for k, v in linha_motivo.items()} if linha_motivo else {}

        return {
            "resumo": {"total_visitas_registradas": total_visitas},
            "desfechos": dados_desfechos,
            "motivos_e_acompanhamentos": motivos,
        }

    async def gerar_relatorio_cadastros(
        self,
        session: AsyncSession,
        id_profissional: int,
        ano: int,
        mes_inicio: int,
        mes_fim: int,
    ) -> dict[str, Any]:
        sql = """
            WITH cad_individual AS (
                SELECT 
                    COUNT(1) AS total_cadastros_individuais,
                    COALESCE(SUM(ci.st_recusa_cadastro), 0) AS recusas_individual,
                    COALESCE(SUM(ci.st_responsavel_familiar), 0) AS responsavel_familiar,
                    COALESCE(SUM(ci.st_plano_saude_privado), 0) AS cad_plano_saude,
                    
                    -- Ciclos de Vida e Condições Crônicas
                    COALESCE(SUM(ci.st_gestante), 0) AS cad_gestantes,
                    COALESCE(SUM(ci.st_hipertensao_arterial), 0) AS cad_hipertensos,
                    COALESCE(SUM(ci.st_diabete), 0) AS cad_diabeticos,
                    COALESCE(SUM(ci.st_doenca_cardiaca), 0) AS cad_cardiaca,
                    COALESCE(SUM(ci.st_avc), 0) AS cad_avc,
                    COALESCE(SUM(ci.st_infarto), 0) AS cad_rins,
                    COALESCE(SUM(ci.st_cancer), 0) AS cad_cancer,
                    COALESCE(SUM(ci.st_doenca_respiratoria), 0) AS cad_respiratoria,
                    COALESCE(SUM(ci.st_hanseniase), 0) AS cad_hanseniase,
                    COALESCE(SUM(ci.st_tuberculose), 0) AS cad_tuberculose,
                    
                    -- Risco Clínico, Acessibilidade e Hábitos
                    COALESCE(SUM(ci.st_internacao_12), 0) AS cad_internacao_recente,
                    COALESCE(SUM(ci.st_acamado), 0) AS cad_acamados,
                    COALESCE(SUM(ci.st_domiciliado), 0) AS cad_domiciliados,
                    COALESCE(SUM(ci.st_tratamento_psiquiatra), 0) AS cad_tratamento_psiquiatrico,
                    COALESCE(SUM(ci.st_fumante), 0) AS cad_fumantes,
                    COALESCE(SUM(ci.st_alcool), 0) AS cad_alcool,
                    COALESCE(SUM(ci.st_outra_droga), 0) AS cad_drogas,
                    COALESCE(SUM(ci.st_usa_planta_medicinal), 0) AS cad_planta_medicinal,
                    COALESCE(SUM(ci.st_pic), 0) AS cad_praticas_integrativas,
                    
                    -- Deficiências Específicas
                    COALESCE(SUM(ci.st_deficiencia), 0) AS cad_deficiencia_total,
                    COALESCE(SUM(ci.st_defi_auditiva), 0) AS cad_deficiencia_auditiva,
                    COALESCE(SUM(ci.st_defi_visual), 0) AS cad_deficiencia_visual,
                    COALESCE(SUM(ci.st_defi_fisica), 0) AS cad_deficiencia_fisica,
                    COALESCE(SUM(ci.st_defi_intelectual_cognitiva), 0) AS cad_deficiencia_cognitiva,
                    COALESCE(SUM(ci.st_defi_tea), 0) AS cad_tea_autismo,
                    
                    -- Vulnerabilidade Social e Segurança Alimentar
                    COALESCE(SUM(ci.st_recebe_beneficio), 0) AS cad_recebe_beneficio_total,
                    COALESCE(SUM(ci.st_beneficio_bolsa_familia), 0) AS cad_bolsa_familia,
                    COALESCE(SUM(ci.st_beneficio_aposentado), 0) AS cad_aposentados,
                    COALESCE(SUM(ci.st_beneficio_prest_continuada), 0) AS cad_bpc,
                    COALESCE(SUM(ci.st_beneficio_cesta_alimento), 0) AS cad_cesta_alimentos,
                    COALESCE(SUM(ci.st_morador_rua), 0) AS cad_morador_rua,
                    COALESCE(SUM(ci.st_alimentos_acab_sem_dinheiro), 0) AS cad_inseguranca_alimentar_1,
                    COALESCE(SUM(ci.st_comeu_que_tinha_dnheir_acab), 0) AS cad_inseguranca_alimentar_2,
                    COALESCE(SUM(ci.st_nao_possui_cpf), 0) AS cad_sem_cpf
                FROM tb_fat_cad_individual ci
                JOIN tb_dim_tempo t ON t.co_seq_dim_tempo = ci.co_dim_tempo
                WHERE ci.co_dim_profissional = :id_prof
                  AND t.nu_ano = :ano AND t.nu_mes BETWEEN :mes_inicio AND :mes_fim
            ),
            cad_domiciliar AS (
                SELECT 
                    COUNT(1) AS total_domicilios,
                    COALESCE(SUM(cd.st_recusa_cadastro), 0) AS recusas_domicilio,
                    COALESCE(SUM(cd.qt_morador), 0) AS total_moradores_declarados,
                    COALESCE(AVG(cd.nu_comodo), 0)::numeric(10,1) AS media_comodos,
                    COALESCE(SUM(cd.st_disp_energia), 0) AS com_energia_eletrica,
                    COALESCE(SUM(cd.st_animal_domiciliar), 0) AS domicilios_com_animais,
                    COALESCE(SUM(cd.st_animal_cachorro), 0) AS com_cachorro,
                    COALESCE(SUM(cd.st_animal_gato), 0) AS com_gato,
                    COALESCE(SUM(cd.st_animal_galinha), 0) AS com_galinha,
                    COALESCE(SUM(cd.st_animal_porco), 0) AS com_porco,
                    COALESCE(SUM(cd.st_animal_passaro), 0) AS com_passaro,
                    COALESCE(SUM(cd.st_animal_outros), 0) AS com_outros_animais
                FROM tb_fat_cad_domiciliar cd
                JOIN tb_dim_tempo t ON t.co_seq_dim_tempo = cd.co_dim_tempo
                WHERE cd.co_dim_profissional = :id_prof
                  AND t.nu_ano = :ano AND t.nu_mes BETWEEN :mes_inicio AND :mes_fim
            )
            SELECT * 
            FROM cad_individual
            CROSS JOIN cad_domiciliar;
        """

        parametros = {
            "id_prof": id_profissional,
            "ano": ano,
            "mes_inicio": mes_inicio,
            "mes_fim": mes_fim,
        }
        res = await session.execute(text(sql), parametros)
        linha = res.mappings().first()

        return dict(linha) if linha else {}

    async def gerar_relatorio_procedimentos(
        self,
        session: AsyncSession,
        id_profissional: int,
        ano: int,
        mes_inicio: int,
        mes_fim: int,
        dias_desconto: int = 0,
    ) -> dict[str, Any]:
        """Gera o relatório com análise mensal, calendário útil e distribuição diária detalhada."""

        # 1. Procedimentos SIGTAP
        sql_sigtap = """
            SELECT 
                p.co_proced AS codigo_sigtap,
                p.ds_proced AS procedimento,
                COUNT(1) AS quantidade
            FROM tb_fat_proced_atend_proced fp
            JOIN tb_dim_tempo t ON t.co_seq_dim_tempo = fp.co_dim_tempo
            JOIN tb_dim_procedimento p ON p.co_seq_dim_procedimento = fp.co_dim_procedimento
            WHERE fp.co_dim_profissional = :id_prof
              AND t.nu_ano = :ano AND t.nu_mes BETWEEN :mes_inicio AND :mes_fim
            GROUP BY p.co_proced, p.ds_proced
            ORDER BY quantidade DESC;
        """

        # 2. Agrupamento Mensal
        sql_evolucao = """
            SELECT 
                t.nu_mes AS mes,
                COUNT(1) AS quantidade,
                COUNT(DISTINCT fp.co_dim_tempo) as dias_com_registro
            FROM tb_fat_proced_atend_proced fp
            JOIN tb_dim_tempo t ON t.co_seq_dim_tempo = fp.co_dim_tempo
            WHERE fp.co_dim_profissional = :id_prof
              AND t.nu_ano = :ano AND t.nu_mes BETWEEN :mes_inicio AND :mes_fim
            GROUP BY t.nu_mes
            ORDER BY t.nu_mes;
        """

        # 3. Registros Diários (Seção 3 do Relatório)
        sql_diario = """
            SELECT 
                t.nu_ano AS ano,
                t.nu_mes AS mes,
                t.nu_dia AS dia,
                LPAD(t.nu_dia::text, 2, '0') || '/' || LPAD(t.nu_mes::text, 2, '0') || '/' || t.nu_ano::text AS data_formatada,
                COUNT(1) AS quantidade
            FROM tb_fat_proced_atend_proced fp
            JOIN tb_dim_tempo t ON t.co_seq_dim_tempo = fp.co_dim_tempo
            WHERE fp.co_dim_profissional = :id_prof
              AND t.nu_ano = :ano AND t.nu_mes BETWEEN :mes_inicio AND :mes_fim
            GROUP BY t.nu_ano, t.nu_mes, t.nu_dia
            ORDER BY t.nu_ano ASC, t.nu_mes ASC, t.nu_dia ASC;
        """

        parametros = {
            "id_prof": id_profissional,
            "ano": ano,
            "mes_inicio": mes_inicio,
            "mes_fim": mes_fim,
        }

        res_sigtap = await session.execute(text(sql_sigtap), parametros)
        res_evolucao = await session.execute(text(sql_evolucao), parametros)
        res_diario = await session.execute(text(sql_diario), parametros)

        linhas_sigtap = res_sigtap.mappings().all()
        linhas_evolucao = {r["mes"]: r for r in res_evolucao.mappings().all()}
        linhas_diario = res_diario.mappings().all()

        detalhamento = [
            {
                "codigo_sigtap": r["codigo_sigtap"],
                "procedimento": r["procedimento"],
                "quantidade": r["quantidade"],
            }
            for r in linhas_sigtap
        ]

        # Montagem dos Registros Diários e Detecção de Pico
        registros_diarios = []
        maior_volume_dia = {"data": "-", "quantidade": 0}

        for r in linhas_diario:
            qtd = int(r["quantidade"])
            data_str = r["data_formatada"]
            registros_diarios.append({"data": data_str, "quantidade": qtd})
            if qtd > maior_volume_dia["quantidade"]:
                maior_volume_dia = {"data": data_str, "quantidade": qtd}

        # Montagem da Evolução Mensal com Dias Úteis e Porcentagem Efetiva
        meses_nomes = {
            1: "Jan",
            2: "Fev",
            3: "Mar",
            4: "Abr",
            5: "Mai",
            6: "Jun",
            7: "Jul",
            8: "Ago",
            9: "Set",
            10: "Out",
            11: "Nov",
            12: "Dez",
        }

        evolucao_mensal = []
        total_geral = 0
        total_dias_registro = 0
        total_dias_mes_geral = 0
        total_dias_uteis_geral = 0
        meses_com_registro = 0

        for mes_num in range(mes_inicio, mes_fim + 1):
            dias_no_mes, dias_uteis_mes = self._obter_metricas_calendario_mes(
                ano, mes_num
            )
            total_dias_mes_geral += dias_no_mes
            total_dias_uteis_geral += dias_uteis_mes

            reg_mes = linhas_evolucao.get(mes_num)
            if reg_mes:
                qtd_mes = reg_mes["quantidade"]
                dias_reg_mes = reg_mes["dias_com_registro"]
                media_dia_mes = (
                    round(qtd_mes / dias_reg_mes, 2) if dias_reg_mes > 0 else 0
                )
                pct_efetiva = (
                    round((dias_reg_mes / dias_uteis_mes) * 100, 1)
                    if dias_uteis_mes > 0
                    else 0
                )
                meses_com_registro += 1
            else:
                qtd_mes = 0
                dias_reg_mes = 0
                media_dia_mes = 0
                pct_efetiva = 0.0

            total_geral += qtd_mes
            total_dias_registro += dias_reg_mes

            evolucao_mensal.append(
                {
                    "mes_numero": mes_num,
                    "mes": meses_nomes.get(mes_num, str(mes_num)),
                    "dias_calendario": dias_no_mes,
                    "dias_uteis": dias_uteis_mes,
                    "dias_com_registro": dias_reg_mes,
                    "percentual_dias_efetivos": pct_efetiva,
                    "quantidade": qtd_mes,
                    "media_dia": media_dia_mes,
                }
            )

        # Cálculo Geral de Produtividade e Calendário
        dias_uteis_esperados = max(0, total_dias_uteis_geral - dias_desconto)
        media_dia_registrado = (
            round(total_geral / total_dias_registro, 2)
            if total_dias_registro > 0
            else 0
        )
        media_dia_teorico = (
            round(total_geral / dias_uteis_esperados, 2)
            if dias_uteis_esperados > 0
            else 0
        )
        pct_geral_efetiva = (
            round((total_dias_registro / dias_uteis_esperados) * 100, 1)
            if dias_uteis_esperados > 0
            else 0
        )

        return {
            "resumo": {
                "total_procedimentos": total_geral,
                "meses_com_registro": meses_com_registro,
                "dias_com_registro": total_dias_registro,
                "total_dias_calendario": total_dias_mes_geral,
                "dias_uteis_esperados": dias_uteis_esperados,
                "percentual_dias_efetivos_geral": pct_geral_efetiva,
                "media_por_dia_registrado": media_dia_registrado,
                "media_por_dia_esperado": media_dia_teorico,
                "maior_volume_dia": maior_volume_dia,
            },
            "evolucao_mensal": evolucao_mensal,
            "registros_diarios": registros_diarios,
            "detalhamento": detalhamento,
        }

    async def gerar_relatorio_executivo(
        self,
        session: AsyncSession,
        id_profissional: int,
        ano: int,
        mes_inicio: int,
        mes_fim: int,
    ) -> dict[str, Any]:
        """
        Orquestra as 3 queries vitais em paralelo e cruza os dados com base em métricas
        do Ministério da Saúde, Previne Brasil e MP, gerando alertas (Verde, Amarelo, Vermelho).
        """
        cadastros = await self.gerar_relatorio_cadastros(
            session, id_profissional, ano, mes_inicio, mes_fim
        )
        visitas = await self.gerar_relatorio_visitas(
            session, id_profissional, ano, mes_inicio, mes_fim
        )
        matriz = await self.gerar_matriz_producao(
            session, id_profissional, ano, mes_inicio, mes_fim
        )

        # 1. Extração Segura de Variáveis (com default 0)
        cidadaos_adscritos = int(cadastros.get("total_cadastros_individuais", 0))
        gestantes_cad = int(cadastros.get("cad_gestantes", 0))
        hipertensos_cad = int(cadastros.get("cad_hipertensos", 0))
        diabeticos_cad = int(cadastros.get("cad_diabeticos", 0))

        resumo_visitas = visitas.get("resumo", {})
        total_visitas = int(resumo_visitas.get("total_visitas_registradas", 0))

        visitas_sucesso = sum(
            int(d["total"])
            for d in visitas.get("desfechos", [])
            if "realizada" in d["desfecho"].lower()
        )

        motivos = visitas.get("motivos_e_acompanhamentos", {})
        visitas_gestante = int(motivos.get("acomp_gestante", 0))
        visitas_has = int(motivos.get("acomp_pessoa_hipertensao", 0))
        visitas_dm = int(motivos.get("acomp_pessoa_diabetes", 0))
        visitas_acamados = int(motivos.get("acomp_domiciliados_acamados", 0))

        # 2. Lógica de Conformidade Legal e Alertas
        taxa_cobertura = (
            round((visitas_sucesso / cidadaos_adscritos), 2)
            if cidadaos_adscritos > 0
            else 0
        )
        if taxa_cobertura >= 1.5:
            status_pnab = {"status": "verde", "msg": "Cobertura Territorial Excelente"}
        elif taxa_cobertura >= 1.0:
            status_pnab = {"status": "verde", "msg": "Cobertura Territorial Conforme"}
        elif taxa_cobertura >= 0.5:
            status_pnab = {
                "status": "amarelo",
                "msg": "Baixa Cobertura: Necessita Revisão",
            }
        else:
            status_pnab = {
                "status": "vermelho",
                "msg": "Risco Crítico de Desassistência e Perda de Repasse",
            }

        if gestantes_cad == 0:
            status_materno = {
                "status": "amarelo",
                "msg": "Nenhuma gestante no cadastro. Busca ativa recomendada.",
            }
        else:
            taxa_gestante = round(visitas_gestante / gestantes_cad, 2)
            if taxa_gestante >= 1.0:
                status_materno = {
                    "status": "verde",
                    "msg": "Acompanhamento materno satisfatório.",
                }
            else:
                deficit = gestantes_cad - visitas_gestante
                status_materno = {
                    "status": "vermelho",
                    "msg": f"Alerta Crítico: {deficit} gestantes com possível desassistência ou falha de registro.",
                }

        if hipertensos_cad == 0 and diabeticos_cad == 0:
            status_cronicos = {
                "status": "amarelo",
                "msg": "Subnotificação suspeita de pacientes crônicos.",
            }
        else:
            visitas_cronicas = visitas_has + visitas_dm
            pacientes_cronicos = hipertensos_cad + diabeticos_cad
            if visitas_cronicas >= pacientes_cronicos:
                status_cronicos = {
                    "status": "verde",
                    "msg": "Cobertura de Crônicos Conforme Normativa",
                }
            else:
                status_cronicos = {
                    "status": "vermelho",
                    "msg": "Déficit no acompanhamento de grupos de risco",
                }

        if visitas_acamados > 0:
            status_vulnerabilidade = {
                "status": "verde",
                "msg": "Assistência ao grupo acamado comprovada",
            }
        else:
            status_vulnerabilidade = {
                "status": "amarelo",
                "msg": "Sem registro de acompanhamento a acamados",
            }

        return {
            "meta_informacao": {
                "cidadaos_adscritos": cidadaos_adscritos,
                "visitas_com_sucesso": visitas_sucesso,
                "visitas_totais": total_visitas,
                "taxa_cobertura_habitante": taxa_cobertura,
            },
            "auditoria": {
                "pnab": {
                    "diretriz": "Cobertura Universal Territorial (Mínimo 1 visita/hab/ano)",
                    "resultado": status_pnab,
                    "numeros": f"{visitas_sucesso} Visitas (Sucesso) para {cidadaos_adscritos} Cadastrados",
                },
                "materno_infantil": {
                    "diretriz": "Rede Cegonha: Prevenção Materno-Infantil",
                    "resultado": status_materno,
                    "numeros": f"{visitas_gestante} Registros para {gestantes_cad} Gestantes Cadastradas",
                },
                "cronicos": {
                    "diretriz": "Acompanhamento Contínuo (HAS / DM)",
                    "resultado": status_cronicos,
                    "numeros": f"{visitas_has + visitas_dm} Registros para {hipertensos_cad + diabeticos_cad} Pacientes",
                },
                "equidade": {
                    "diretriz": "Prioridade e Acessibilidade (Acamados e Domiciliados)",
                    "resultado": status_vulnerabilidade,
                    "numeros": f"{visitas_acamados} registros de acompanhamento a domiciliados",
                },
            },
            "dados_brutos": {
                "matriz": matriz,
                "visitas": visitas,
                "cadastros": cadastros,
            },
        }

    async def gerar_relatorio_consultas_odonto(
        self,
        session: AsyncSession,
        id_profissional: int,
        ano: int,
        mes_inicio: int,
        mes_fim: int,
    ) -> dict[str, Any]:
        """
        Gera o relatório consolidado de atendimentos odontológicos: perfil demográfico,
        vigilância em saúde bucal, condutas clínicas e encaminhamentos ao CEO.
        """
        sql = """
            SELECT 
                t.nu_mes AS mes,
                COUNT(1) AS total_atendimentos,

                -- Perfil e Populações Prioritárias
                COALESCE(SUM(f.st_gestante), 0) AS gestantes_atendidas,
                COALESCE(SUM(f.st_paciente_necessidades_espec), 0) AS pac_necessidades_especiais,

                -- Condutas Clínicas e Desfechos
                COALESCE(SUM(f.st_conduta_tratamento_concluid), 0) AS tratamentos_concluidos,
                COALESCE(SUM(f.st_conduta_consulta_agendada), 0) AS retornos_agendados,
                COALESCE(SUM(f.st_conduta_alta_episodio), 0) AS altas_episodio,

                -- Vigilância em Saúde Bucal
                COALESCE(SUM(f.st_vigil_dor_dente), 0) AS queixa_dor_dente,
                COALESCE(SUM(f.st_vigil_abscesso_dentoalveola), 0) AS abscesso_dentoalveolar,
                COALESCE(SUM(f.st_vigil_traumat_dentoalveolar), 0) AS traumatismo_dental,
                COALESCE(SUM(f.st_vigil_alterac_tecidos_moles), 0) AS lesao_tecidos_moles,
                COALESCE(SUM(f.st_vigil_fluorose_dentaria), 0) AS fluorose_dentaria,

                -- Fornecimento de Insumos Básicos
                COALESCE(SUM(f.st_fornecimento_escova_dental), 0) AS escovas_entregues,
                COALESCE(SUM(f.st_fornecimento_creme_dental), 0) AS cremes_entregues,
                COALESCE(SUM(f.st_fornecimento_fio_dental), 0) AS fios_entregues,

                -- Encaminhamentos Especializados (CEO)
                COALESCE(SUM(f.st_encaminhamento_endodontia), 0) AS encam_endodontia,
                COALESCE(SUM(f.st_encaminhamento_cirurgia_bmf), 0) AS encam_bucomaxilo,
                COALESCE(SUM(f.st_encaminhamento_periodontia), 0) AS encam_periodontia,
                COALESCE(SUM(f.st_encaminhamento_protese_dent), 0) AS encam_protese,
                COALESCE(SUM(f.st_encaminhamento_odontopediat), 0) AS encam_odontopediatria,
                COALESCE(SUM(f.st_encaminhamento_estomatologi), 0) AS encam_estomatologia
            FROM tb_fat_atendimento_odonto f
            JOIN tb_dim_tempo t ON t.co_seq_dim_tempo = f.co_dim_tempo
            WHERE f.co_dim_profissional_1 = :id_prof
              AND t.nu_ano = :ano AND t.nu_mes BETWEEN :mes_inicio AND :mes_fim
            GROUP BY t.nu_mes
            ORDER BY t.nu_mes ASC;
        """

        parametros = {
            "id_prof": id_profissional,
            "ano": ano,
            "mes_inicio": mes_inicio,
            "mes_fim": mes_fim,
        }
        res = await session.execute(text(sql), parametros)
        linhas = res.mappings().all()

        meses_nomes = {
            1: "Jan",
            2: "Fev",
            3: "Mar",
            4: "Abr",
            5: "Mai",
            6: "Jun",
            7: "Jul",
            8: "Ago",
            9: "Set",
            10: "Out",
            11: "Nov",
            12: "Dez",
        }

        evolucao_mensal = []
        totais = {
            "total_atendimentos": 0,
            "gestantes_atendidas": 0,
            "pac_necessidades_especiais": 0,
            "tratamentos_concluidos": 0,
            "retornos_agendados": 0,
            "altas_episodio": 0,
            "queixa_dor_dente": 0,
            "abscesso_dentoalveolar": 0,
            "traumatismo_dental": 0,
            "lesao_tecidos_moles": 0,
            "fluorose_dentaria": 0,
            "escovas_entregues": 0,
            "cremes_entregues": 0,
            "fios_entregues": 0,
            "encam_endodontia": 0,
            "encam_bucomaxilo": 0,
            "encam_periodontia": 0,
            "encam_protese": 0,
            "encam_odontopediatria": 0,
            "encam_estomatologia": 0,
        }

        for r in linhas:
            mes_num = r["mes"]
            evolucao_mensal.append(
                {
                    "mes_numero": mes_num,
                    "mes": meses_nomes.get(mes_num, str(mes_num)),
                    **{k: int(v) for k, v in r.items() if k != "mes"},
                }
            )
            for k in totais:
                totais[k] += int(r[k] or 0)

        return {
            "resumo": totais,
            "evolucao_mensal": evolucao_mensal,
        }

    async def gerar_relatorio_procedimentos_odonto(
        self,
        session: AsyncSession,
        id_profissional: int,
        ano: int,
        mes_inicio: int,
        mes_fim: int,
    ) -> dict[str, Any]:
        """
        Agrupa e categoriza os procedimentos realizados na cadeira odontológica (SIGTAP),
        aplicando saneamento para códigos atípicos e descrições idênticas registradas
        em tabelas/formatos diferentes pelo PEC.
        """
        sql = """
            SELECT 
                p.co_proced AS codigo_sigtap,
                p.ds_proced AS procedimento,
                SUM(fp.qt_procedimentos) AS quantidade
            FROM tb_fat_atend_odonto_proced fp
            JOIN tb_dim_tempo t ON t.co_seq_dim_tempo = fp.co_dim_tempo
            JOIN tb_dim_procedimento p ON p.co_seq_dim_procedimento = fp.co_dim_procedimento
            WHERE fp.co_dim_profissional_1 = :id_prof
              AND t.nu_ano = :ano AND t.nu_mes BETWEEN :mes_inicio AND :mes_fim
            GROUP BY p.co_proced, p.ds_proced
        """

        parametros = {
            "id_prof": id_profissional,
            "ano": ano,
            "mes_inicio": mes_inicio,
            "mes_fim": mes_fim,
        }
        res = await session.execute(text(sql), parametros)
        linhas = res.mappings().all()

        detalhamento = []
        total_procedimentos = 0
        procedimentos_agregados = {}

        # 1. Agrega procedimentos com exatamente a mesma descrição (mesmo que códigos difiram)
        for r in linhas:
            cod = r["codigo_sigtap"].strip()
            desc = r["procedimento"].strip()

            # SANEAMENTO DE NOMENCLATURAS: Padroniza variações de nomes do e-SUS PEC
            if "RETIRADA DE PONTOS DE CIRURGIAS" in desc.upper():
                desc = "RETIRADA DE PONTOS DE CIRURGIAS"

            qtd = int(r["quantidade"] or 0)

            if desc not in procedimentos_agregados:
                procedimentos_agregados[desc] = {
                    "codigo_sigtap": cod,
                    "procedimento": desc,
                    "quantidade": 0,
                }
            else:
                # Se o procedimento existe com um código diferente (ex: ABPG018 vs SIGTAP oficial),
                # concatena os códigos para não perder a origem na auditoria visual.
                if cod not in procedimentos_agregados[desc]["codigo_sigtap"]:
                    procedimentos_agregados[desc]["codigo_sigtap"] += f" / {cod}"

            procedimentos_agregados[desc]["quantidade"] += qtd

        # 2. Classificação clínica para saúde bucal (Com palavras-chave corrigidas)
        categorias_procedimentos = {
            "prevencao": {
                "titulo": "Prevenção e Atenção Básica",
                "total": 0,
                "itens": [],
            },
            "dentistica": {
                "titulo": "Dentística Restauradora",
                "total": 0,
                "itens": [],
            },
            "periodontia": {
                "titulo": "Periodontia e Profilaxia",
                "total": 0,
                "itens": [],
            },
            "cirurgia": {"titulo": "Cirurgia e Exodontias", "total": 0, "itens": []},
            "endodontia": {"titulo": "Endodontia e Urgência", "total": 0, "itens": []},
            "outros": {"titulo": "Outros Procedimentos", "total": 0, "itens": []},
        }

        # 3. Distribuição para os grupos baseados nos nomes saneados
        for item in procedimentos_agregados.values():
            desc = item["procedimento"]
            qtd = item["quantidade"]
            total_procedimentos += qtd

            detalhamento.append(item)

            desc_upper = desc.upper()
            if any(
                term in desc_upper
                for term in [
                    "HIGIENE BUCAL",
                    "FLÚOR",
                    "SELAMENTO",
                    "SELANTE",
                    "PROGRAMÁTICA",
                    "COMPORTAMENTO",
                ]
            ):
                cat_alvo = "prevencao"
            elif any(
                term in desc_upper
                for term in [
                    "RESTAURAÇÃO",
                    "RESINA",
                    "IONÔMERO",
                    "TRA/ART",
                    "RESTAURADOR",
                ]
            ):
                cat_alvo = "dentistica"
            elif any(
                term in desc_upper
                for term in ["RASPAGEM", "PROFILAXIA", "PLACA BACTERIANA"]
            ):
                cat_alvo = "periodontia"
            elif any(
                term in desc_upper
                for term in [
                    "EXODONTIA",
                    "SUTURA",
                    "CIRURGIA",
                    "ODONTOSECÇÃO",
                    "PONTOS",
                    "DRENAGEM",
                    "ABSCESSO",
                ]
            ):
                cat_alvo = "cirurgia"
            elif any(
                term in desc_upper
                for term in [
                    "POLPA",
                    "CURATIVO",
                    "URGÊNCIA",
                    "PULPAR",
                    "BIOMECANICO",
                    "PULPOTOMIA",
                ]
            ):
                cat_alvo = "endodontia"
            else:
                cat_alvo = "outros"

            categorias_procedimentos[cat_alvo]["total"] += qtd
            categorias_procedimentos[cat_alvo]["itens"].append(item)

        return {
            "resumo": {
                "total_procedimentos": total_procedimentos,
                "total_tipos_distintos": len(detalhamento),
            },
            "categorias": categorias_procedimentos,
            "detalhamento": sorted(
                detalhamento, key=lambda x: x["quantidade"], reverse=True
            ),
        }

    # ==========================================
    # MÉTODOS DA SPRINT 3: AUDITORIA MÉDICA E CLÍNICA
    # ==========================================

    async def buscar_lotacoes_historicas_profissional(
        self, session: AsyncSession, id_profissional: int, ano: int
    ) -> list[dict[str, Any]]:
        """Mapeia todas as UBS e Equipes onde o profissional atuou no ano para preencher o Dropdown (Filtro)."""
        query = text("""
            SELECT 
                dus.nu_cnes AS cnes,
                dus.no_unidade_saude AS ubs,
                COALESCE(de.nu_ine, '-') AS ine,
                COALESCE(de.no_equipe, 'Sem Equipe Vinculada') AS equipe,
                COUNT(fai.co_seq_fat_atd_ind) AS total_atendimentos
            FROM tb_fat_atendimento_individual fai
            JOIN tb_dim_tempo t ON t.co_seq_dim_tempo = fai.co_dim_tempo
            JOIN tb_dim_unidade_saude dus ON dus.co_seq_dim_unidade_saude = fai.co_dim_unidade_saude_1
            LEFT JOIN tb_dim_equipe de ON de.co_seq_dim_equipe = fai.co_dim_equipe_1
            WHERE fai.co_dim_profissional_1 = :id_prof
              AND t.nu_ano = :ano
            GROUP BY dus.nu_cnes, dus.no_unidade_saude, de.nu_ine, de.no_equipe
            ORDER BY total_atendimentos DESC;
        """)
        resultado = await session.execute(
            query, {"id_prof": id_profissional, "ano": ano}
        )
        return [dict(row._mapping) for row in resultado.all()]

    async def buscar_lotacao_principal_medico(
        self,
        session: AsyncSession,
        id_profissional: int,
        ano: int,
        mes_inicio: int,
        mes_fim: int,
        cnes: str | None = None,
    ) -> dict[str, str]:
        """Identifica a UBS e Equipe onde o profissional teve maior volume de atendimentos (Filtra por CNES se passado)."""
        filtro_cnes = "AND dus.nu_cnes = :cnes" if cnes else ""
        query = text(f"""
            SELECT 
                dp.no_profissional AS nome,
                cbo.no_cbo AS cbo,
                dus.no_unidade_saude AS ubs,
                COALESCE(de.no_equipe, 'Sem Equipe Vinculada') AS equipe,
                dus.nu_cnes AS cnes,
                COALESCE(de.nu_ine, '-') AS ine
            FROM tb_fat_atendimento_individual fai
            JOIN tb_dim_tempo t ON t.co_seq_dim_tempo = fai.co_dim_tempo
            JOIN tb_dim_profissional dp ON dp.co_seq_dim_profissional = fai.co_dim_profissional_1
            JOIN tb_dim_cbo cbo ON cbo.co_seq_dim_cbo = fai.co_dim_cbo_1
            JOIN tb_dim_unidade_saude dus ON dus.co_seq_dim_unidade_saude = fai.co_dim_unidade_saude_1
            LEFT JOIN tb_dim_equipe de ON de.co_seq_dim_equipe = fai.co_dim_equipe_1
            WHERE fai.co_dim_profissional_1 = :id_prof 
              AND t.nu_ano = :ano
              AND t.nu_mes BETWEEN :mes_inicio AND :mes_fim
              {filtro_cnes}
            GROUP BY dp.no_profissional, cbo.no_cbo, dus.no_unidade_saude, de.no_equipe, dus.nu_cnes, de.nu_ine
            ORDER BY COUNT(fai.co_seq_fat_atd_ind) DESC
            LIMIT 1;
        """)
        parametros = {
            "id_prof": id_profissional,
            "ano": ano,
            "mes_inicio": mes_inicio,
            "mes_fim": mes_fim,
        }
        if cnes:
            parametros["cnes"] = cnes

        resultado = (await session.execute(query, parametros)).mappings().first()
        if resultado:
            return dict(resultado)
        return {
            "nome": "Profissional Sem Produção",
            "cbo": "-",
            "ubs": "-",
            "equipe": "-",
            "cnes": "-",
            "ine": "-",
        }

    async def gerar_relatorio_consultas_medicas(
        self,
        session: AsyncSession,
        id_profissional: int,
        ano: int,
        mes_inicio: int,
        mes_fim: int,
        cnes: str | None = None,
    ) -> dict[str, Any]:
        """Resumo operacional de consultas, agendas, desfechos e Top CIAP-2 (Isolável por Lotação)."""
        filtro_cnes = (
            "AND fai.co_dim_unidade_saude_1 = (SELECT co_seq_dim_unidade_saude FROM tb_dim_unidade_saude WHERE nu_cnes = :cnes LIMIT 1)"
            if cnes
            else ""
        )

        sql_resumo = f"""
            SELECT 
                COUNT(fai.co_seq_fat_atd_ind) AS total_atendimentos,
                COUNT(CASE WHEN fai.co_dim_tipo_atendimento IN (1, 2, 5, 6) THEN 1 END) AS atendimentos_agendados,
                COUNT(CASE WHEN fai.co_dim_tipo_atendimento NOT IN (1, 2, 5, 6) THEN 1 END) AS demanda_espontanea,
                
                -- Condutas e Desfechos Clínicos
                COUNT(CASE WHEN fai.st_conduta_alta_episodio = 1 THEN 1 END) AS conduta_alta,
                COUNT(CASE WHEN fai.st_conduta_consulta_agendada = 1 THEN 1 END) AS conduta_retorno,
                COUNT(CASE WHEN fai.st_conduta_cuidd_conti_program = 1 THEN 1 END) AS conduta_cuidado_continuado,
                
                -- Encaminhamentos
                COUNT(CASE WHEN fai.st_encaminhamento_serv_special = 1 THEN 1 END) AS conduta_encaminhamento_especialista,
                COUNT(CASE WHEN fai.st_encaminhamento_urgencia = 1 THEN 1 END) AS conduta_encaminhamento_urgencia,
                COUNT(CASE WHEN fai.st_encaminhamento_caps = 1 THEN 1 END) AS conduta_encaminhamento_caps,
                COUNT(CASE WHEN fai.st_encaminhamento_intern_hospi = 1 THEN 1 END) AS conduta_encaminhamento_hospitalar,
                
                -- Solicitação e Avaliação de Exames/Procedimentos
                COUNT(CASE WHEN fai.ds_filtro_proced_solicitados IS NOT NULL AND trim(fai.ds_filtro_proced_solicitados, '|') <> '' THEN 1 END) AS solicitacao_exames,
                COUNT(CASE WHEN fai.ds_filtro_proced_avaliados IS NOT NULL AND trim(fai.ds_filtro_proced_avaliados, '|') <> '' THEN 1 END) AS avaliacao_exames
            FROM tb_fat_atendimento_individual fai
            JOIN tb_dim_tempo t ON t.co_seq_dim_tempo = fai.co_dim_tempo
            WHERE fai.co_dim_profissional_1 = :id_prof
              AND t.nu_ano = :ano AND t.nu_mes BETWEEN :mes_inicio AND :mes_fim
              {filtro_cnes};
        """
        sql_ciap = f"""
            WITH ciaps_explodidos AS (
                SELECT unnest(string_to_array(trim(fai.ds_filtro_ciaps, '|'), '|')) AS codigo_ciap
                FROM tb_fat_atendimento_individual fai
                JOIN tb_dim_tempo t ON t.co_seq_dim_tempo = fai.co_dim_tempo
                WHERE fai.co_dim_profissional_1 = :id_prof
                  AND t.nu_ano = :ano AND t.nu_mes BETWEEN :mes_inicio AND :mes_fim
                  {filtro_cnes}
                  AND fai.ds_filtro_ciaps IS NOT NULL 
                  AND trim(fai.ds_filtro_ciaps, '|') <> '' 
            )
            SELECT 
                c.codigo_ciap, dc.no_ciap AS descricao, COUNT(1) AS quantidade
            FROM ciaps_explodidos c
            JOIN tb_dim_ciap dc ON dc.nu_ciap = c.codigo_ciap
            WHERE trim(c.codigo_ciap) <> ''
            GROUP BY c.codigo_ciap, dc.no_ciap
            ORDER BY quantidade DESC LIMIT 10;
        """
        parametros = {
            "id_prof": id_profissional,
            "ano": ano,
            "mes_inicio": mes_inicio,
            "mes_fim": mes_fim,
        }
        if cnes:
            parametros["cnes"] = cnes

        res_resumo = (
            (await session.execute(text(sql_resumo), parametros)).mappings().first()
        )
        res_ciap = (await session.execute(text(sql_ciap), parametros)).mappings().all()

        return {
            "resumo": dict(res_resumo) if res_resumo else {},
            "top_ciap": [dict(r) for r in res_ciap],
        }

    async def buscar_top_cids_medico(
        self,
        session: AsyncSession,
        id_profissional: int,
        ano: int,
        mes_inicio: int,
        mes_fim: int,
        cnes: str | None = None,
    ) -> list[dict[str, Any]]:
        """Extrai o ranking de CIDs diagnosticados pelo médico (Isolável por Lotação)."""
        filtro_cnes = (
            "AND fai.co_dim_unidade_saude_1 = (SELECT co_seq_dim_unidade_saude FROM tb_dim_unidade_saude WHERE nu_cnes = :cnes LIMIT 1)"
            if cnes
            else ""
        )
        query = text(f"""
            WITH cids_explodidos AS (
                SELECT unnest(string_to_array(trim(fai.ds_filtro_cids, '|'), '|')) AS codigo_cid
                FROM tb_fat_atendimento_individual fai
                JOIN tb_dim_tempo t ON t.co_seq_dim_tempo = fai.co_dim_tempo
                WHERE fai.co_dim_profissional_1 = :id_prof
                  AND t.nu_ano = :ano AND t.nu_mes BETWEEN :mes_inicio AND :mes_fim
                  {filtro_cnes}
                  AND fai.ds_filtro_cids IS NOT NULL AND trim(fai.ds_filtro_cids, '|') <> ''
            )
            SELECT 
                c.codigo_cid, dc.no_cid AS doenca, COUNT(1) AS volume_atendimentos
            FROM cids_explodidos c
            JOIN tb_dim_cid dc ON dc.nu_cid = c.codigo_cid
            WHERE trim(c.codigo_cid) <> ''
            GROUP BY c.codigo_cid, dc.no_cid
            ORDER BY volume_atendimentos DESC LIMIT 10;
        """)
        parametros = {
            "id_prof": id_profissional,
            "ano": ano,
            "mes_inicio": mes_inicio,
            "mes_fim": mes_fim,
        }
        if cnes:
            parametros["cnes"] = cnes
        resultado = await session.execute(query, parametros)
        return [dict(row._mapping) for row in resultado.all()]

    async def calcular_taxa_sinais_vitais_medico(
        self,
        session: AsyncSession,
        id_profissional: int,
        ano: int,
        mes_inicio: int,
        mes_fim: int,
        cnes: str | None = None,
    ) -> dict[str, Any]:
        """Calcula o percentual de preenchimento de PA e Peso (Isolável por Lotação)."""
        filtro_cnes = (
            "AND fai.co_dim_unidade_saude_1 = (SELECT co_seq_dim_unidade_saude FROM tb_dim_unidade_saude WHERE nu_cnes = :cnes LIMIT 1)"
            if cnes
            else ""
        )
        query = text(f"""
            SELECT 
                COUNT(fai.co_seq_fat_atd_ind) AS total_consultas,
                SUM(CASE WHEN fai.nu_pressao_sistolica IS NOT NULL THEN 1 ELSE 0 END) AS consultas_com_pa_aferida,
                SUM(CASE WHEN fai.nu_peso IS NOT NULL THEN 1 ELSE 0 END) AS consultas_com_peso_medido,
                ROUND((SUM(CASE WHEN fai.nu_pressao_sistolica IS NOT NULL THEN 1 ELSE 0 END)::NUMERIC / NULLIF(COUNT(fai.co_seq_fat_atd_ind), 0)) * 100, 2) AS taxa_rastreio_pressao_pct,
                ROUND((SUM(CASE WHEN fai.nu_peso IS NOT NULL THEN 1 ELSE 0 END)::NUMERIC / NULLIF(COUNT(fai.co_seq_fat_atd_ind), 0)) * 100, 2) AS taxa_rastreio_peso_pct
            FROM tb_fat_atendimento_individual fai
            JOIN tb_dim_tempo t ON t.co_seq_dim_tempo = fai.co_dim_tempo
            WHERE fai.co_dim_profissional_1 = :id_prof
              AND t.nu_ano = :ano AND t.nu_mes BETWEEN :mes_inicio AND :mes_fim
              {filtro_cnes};
        """)
        parametros = {
            "id_prof": id_profissional,
            "ano": ano,
            "mes_inicio": mes_inicio,
            "mes_fim": mes_fim,
        }
        if cnes:
            parametros["cnes"] = cnes
        resultado = (await session.execute(query, parametros)).mappings().first()

        if resultado and resultado["total_consultas"] > 0:
            return {
                "total_consultas": resultado["total_consultas"],
                "consultas_com_pa_aferida": resultado["consultas_com_pa_aferida"],
                "consultas_com_peso_medido": resultado["consultas_com_peso_medido"],
                "taxa_rastreio_pressao_pct": float(
                    resultado["taxa_rastreio_pressao_pct"] or 0
                ),
                "taxa_rastreio_peso_pct": float(
                    resultado["taxa_rastreio_peso_pct"] or 0
                ),
            }
        return {
            "total_consultas": 0,
            "consultas_com_pa_aferida": 0,
            "consultas_com_peso_medido": 0,
            "taxa_rastreio_pressao_pct": 0.0,
            "taxa_rastreio_peso_pct": 0.0,
        }

    async def buscar_perfil_demografico_medico(
        self,
        session: AsyncSession,
        id_profissional: int,
        ano: int,
        mes_inicio: int,
        mes_fim: int,
        cnes: str | None = None,
    ) -> dict[str, Any]:
        """Calcula a distribuição etária dinâmica (Idade = Atendimento - Nascimento), Sexo e Gestantes."""
        filtro_cnes = (
            "AND fai.co_dim_unidade_saude_1 = (SELECT co_seq_dim_unidade_saude FROM tb_dim_unidade_saude WHERE nu_cnes = :cnes LIMIT 1)"
            if cnes
            else ""
        )
        query = text(f"""
            SELECT 
                COUNT(fai.co_seq_fat_atd_ind) AS total_atendimentos,
                SUM(CASE WHEN EXTRACT(YEAR FROM AGE(fai.dt_inicial_atendimento, c.dt_nascimento)) BETWEEN 0 AND 2 THEN 1 ELSE 0 END) AS bebes_0_2,
                SUM(CASE WHEN EXTRACT(YEAR FROM AGE(fai.dt_inicial_atendimento, c.dt_nascimento)) BETWEEN 3 AND 11 THEN 1 ELSE 0 END) AS criancas_3_11,
                SUM(CASE WHEN EXTRACT(YEAR FROM AGE(fai.dt_inicial_atendimento, c.dt_nascimento)) BETWEEN 12 AND 17 THEN 1 ELSE 0 END) AS adolescentes_12_17,
                SUM(CASE WHEN EXTRACT(YEAR FROM AGE(fai.dt_inicial_atendimento, c.dt_nascimento)) BETWEEN 18 AND 59 THEN 1 ELSE 0 END) AS adultos_18_59,
                SUM(CASE WHEN EXTRACT(YEAR FROM AGE(fai.dt_inicial_atendimento, c.dt_nascimento)) >= 60 THEN 1 ELSE 0 END) AS idosos_60_mais,
                SUM(CASE WHEN c.no_sexo ILIKE 'M%' THEN 1 ELSE 0 END) AS homens,
                SUM(CASE WHEN c.no_sexo ILIKE 'F%' THEN 1 ELSE 0 END) AS mulheres,
                SUM(CASE WHEN fai.nu_idade_gestacional_semanas IS NOT NULL OR fai.nu_gestas_previas IS NOT NULL THEN 1 ELSE 0 END) AS gestantes
            FROM tb_fat_atendimento_individual fai
            JOIN tb_dim_tempo t ON t.co_seq_dim_tempo = fai.co_dim_tempo
            JOIN tb_fat_cidadao_pec fcp ON fcp.co_seq_fat_cidadao_pec = fai.co_fat_cidadao_pec
            JOIN tb_cidadao c ON c.co_seq_cidadao = fcp.co_cidadao
            WHERE fai.co_dim_profissional_1 = :id_prof
              AND t.nu_ano = :ano AND t.nu_mes BETWEEN :mes_inicio AND :mes_fim
              {filtro_cnes};
        """)
        parametros = {
            "id_prof": id_profissional,
            "ano": ano,
            "mes_inicio": mes_inicio,
            "mes_fim": mes_fim,
        }
        if cnes:
            parametros["cnes"] = cnes
        resultado = (await session.execute(query, parametros)).mappings().first()

        if resultado and resultado["total_atendimentos"] > 0:
            return dict(resultado)
        return {
            "total_atendimentos": 0,
            "bebes_0_2": 0,
            "criancas_3_11": 0,
            "adolescentes_12_17": 0,
            "adultos_18_59": 0,
            "idosos_60_mais": 0,
            "homens": 0,
            "mulheres": 0,
            "gestantes": 0,
        }

    async def calcular_absenteismo_agenda(
        self,
        session: AsyncSession,
        id_profissional: int,
        ano: int,
        mes_inicio: int,
        mes_fim: int,
        cnes: str | None = None,
    ) -> dict[str, Any]:
        """Cruza agendamentos apurando absenteísmo real (Isolável por Lotação)."""
        filtro_cnes = (
            "AND l.co_ator_papel IN (SELECT co_ator_papel FROM tb_lotacao lo JOIN tb_dim_unidade_saude u ON u.co_seq_dim_unidade_saude = lo.co_unidade_saude WHERE u.nu_cnes = :cnes)"
            if cnes
            else ""
        )
        query = text(f"""
            WITH profissional_dim AS (SELECT nu_cns FROM tb_dim_profissional WHERE co_seq_dim_profissional = :id_prof LIMIT 1),
            agenda_normalizada AS (
                SELECT 
                    a.co_seq_agendado,
                    sa.no_situacao_agendado AS status_original,
                    CASE 
                        WHEN sa.no_situacao_agendado IN ('ATENDIMENTO REALIZADO') THEN 'ATENDIDO'
                        WHEN sa.no_situacao_agendado = 'NÃO COMPARECEU' THEN 'FALTA_CONFIRMADA'
                        WHEN sa.no_situacao_agendado = 'AGENDADO' AND a.dt_agendado::date < CURRENT_DATE THEN 'FALTA_POR_INERCIA'
                        WHEN sa.no_situacao_agendado = 'CIDADÃO PRESENTE NA UNIDADE' AND a.dt_agendado::date < CURRENT_DATE THEN 'ABANDONO_SALA_ESPERA'
                        WHEN sa.no_situacao_agendado = 'CANCELADO' THEN 'CANCELADO'
                        ELSE 'AGENDADO_FUTURO'
                    END AS classificacao_auditoria
                FROM tb_agendado a
                JOIN tb_situacao_agendado sa ON sa.co_situacao_agendado = a.st_agendado
                JOIN tb_lotacao l ON l.co_ator_papel = a.co_lotacao_agendada
                JOIN tb_prof p ON p.co_seq_prof = l.co_prof
                JOIN profissional_dim pd ON pd.nu_cns = p.nu_cns
                WHERE EXTRACT(YEAR FROM a.dt_agendado) = :ano
                  AND EXTRACT(MONTH FROM a.dt_agendado) BETWEEN :mes_inicio AND :mes_fim
                  {filtro_cnes}
            )
            SELECT classificacao_auditoria, COUNT(co_seq_agendado) AS total FROM agenda_normalizada GROUP BY classificacao_auditoria;
        """)
        parametros = {
            "id_prof": id_profissional,
            "ano": ano,
            "mes_inicio": mes_inicio,
            "mes_fim": mes_fim,
        }
        if cnes:
            parametros["cnes"] = cnes
        resultado = await session.execute(query, parametros)
        linhas = {row.classificacao_auditoria: row.total for row in resultado.all()}

        atendidos = int(linhas.get("ATENDIDO", 0) or 0)
        faltas_confirmadas = int(linhas.get("FALTA_CONFIRMADA", 0) or 0)
        faltas_inercia = int(linhas.get("FALTA_POR_INERCIA", 0) or 0)
        abandonos_fila = int(linhas.get("ABANDONO_SALA_ESPERA", 0) or 0)
        cancelados = int(linhas.get("CANCELADO", 0) or 0)
        agendados_futuros = int(linhas.get("AGENDADO_FUTURO", 0) or 0)

        total_faltas = faltas_confirmadas + faltas_inercia
        total_ofertado_passado = atendidos + total_faltas + abandonos_fila
        taxa_absenteismo = (
            round((total_faltas / total_ofertado_passado) * 100, 2)
            if total_ofertado_passado > 0
            else 0.0
        )

        return {
            "resumo": {
                "vagas_ofertadas_passado": total_ofertado_passado,
                "atendimentos_realizados": atendidos,
                "total_faltas": total_faltas,
                "faltas_manuais": faltas_confirmadas,
                "faltas_por_inercia_sistema": faltas_inercia,
                "abandonos_fila_recepcao": abandonos_fila,
                "cancelamentos": cancelados,
                "agendamentos_futuros": agendados_futuros,
                "taxa_absenteismo_pct": taxa_absenteismo,
            },
            "alerta_gerencial": "Alto índice de agendas não fechadas"
            if faltas_inercia > faltas_confirmadas
            else "Fluxo de fechamento adequado",
        }

    async def buscar_top_procedimentos_avaliados_medico(
        self,
        session: AsyncSession,
        id_profissional: int,
        ano: int,
        mes_inicio: int,
        mes_fim: int,
        limite: int = 10,
        cnes: str | None = None,
    ) -> list[dict[str, Any]]:
        """Extrai o ranking de procedimentos e exames solicitados (Isolável por Lotação)."""
        filtro_cnes = (
            "AND fai.co_dim_unidade_saude_1 = (SELECT co_seq_dim_unidade_saude FROM tb_dim_unidade_saude WHERE nu_cnes = :cnes LIMIT 1)"
            if cnes
            else ""
        )
        query = text(f"""
            WITH proced_explodidos AS (
                SELECT unnest(string_to_array(trim(fai.ds_filtro_proced_avaliados, '|'), '|')) AS codigo_procedimento
                FROM tb_fat_atendimento_individual fai
                JOIN tb_dim_tempo t ON t.co_seq_dim_tempo = fai.co_dim_tempo
                WHERE fai.co_dim_profissional_1 = :id_prof
                  AND t.nu_ano = :ano AND t.nu_mes BETWEEN :mes_inicio AND :mes_fim
                  {filtro_cnes}
                  AND fai.ds_filtro_proced_avaliados IS NOT NULL AND trim(fai.ds_filtro_proced_avaliados, '|') <> ''
            )
            SELECT 
                c.codigo_procedimento, COALESCE(dim.ds_proced, pr.no_proced, 'Procedimento Não Localizado') AS nome_procedimento,
                COUNT(1) AS total_realizado
            FROM proced_explodidos c
            LEFT JOIN tb_dim_procedimento dim ON dim.co_proced = c.codigo_procedimento
            LEFT JOIN tb_proced pr ON pr.co_proced = c.codigo_procedimento
            WHERE trim(c.codigo_procedimento) <> ''
            GROUP BY 1, 2
            ORDER BY total_realizado DESC LIMIT :limite;
        """)
        parametros = {
            "id_prof": id_profissional,
            "ano": ano,
            "mes_inicio": mes_inicio,
            "mes_fim": mes_fim,
            "limite": limite,
        }
        if cnes:
            parametros["cnes"] = cnes
        resultado = await session.execute(query, parametros)
        return [dict(row._mapping) for row in resultado.all()]


service = RelatoriosService()
