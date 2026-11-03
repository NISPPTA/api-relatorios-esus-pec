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
}

# Mapeamento do nome do grupo para as chaves do catálogo
MAPEAMENTO_GRUPOS: dict[str, list[str]] = {
    "ACS - AGENTE COMUNITÁRIO DE SAÚDE": [
        "visitas_domiciliares",
        "cadastros_territoriais",
    ],
    "ACE - AGENTE DE COMBATE ÀS ENDEMIAS": [
        "visitas_endemias",
    ],
    "MÉDICO": [
        "consultas_medicas",
        "procedimentos_ambulatoriais",
    ],
    "ENFERMEIRO": [
        "consultas_enfermagem",
        "procedimentos_ambulatoriais",
        "vacinacao_administrada",
    ],
    "AUXILIAR OU TÉCNICO DE ENFERMAGEM": [
        "procedimentos_ambulatoriais",
        "vacinacao_administrada",
    ],
    "CIRURGIÃO DENTISTA": [
        "consultas_odontologicas",
        "procedimentos_odonto",
    ],
    "ASB - AUXILIAR DE SAÚDE BUCAL": [
        "procedimentos_odonto",
    ],
    "TSB - TÉCNICO DE SAÚDE BUCAL": [
        "procedimentos_odonto",
    ],
    "OUTRO PROF. NÍVEL SUPERIOR": [
        "atendimentos_emulti",
        "atividades_coletivas",
        "procedimentos_ambulatoriais",
    ],
    "OUTRO PROF. NÍVEL MÉDIO/TÉCNICO": [
        "procedimentos_ambulatoriais",
    ],
    "ADMINISTRATIVO / RECEPÇÃO": [
        "cadastros_recepcao",
    ],
    "DIGITADOR": [
        "cadastros_recepcao",
    ],
}


class RelatoriosService:
    def _resolver_relatorios_para_grupos(
        self, grupos: list[str]
    ) -> list[RelatorioDisponivel]:
        """Calcula a união única de relatórios disponíveis a partir da lista de grupos."""
        chaves_resolvidas = {
            "matriz_serie_historica"
        }  # Todos têm direito à Matriz Geral

        for grupo in grupos:
            chaves = MAPEAMENTO_GRUPOS.get(grupo, [])
            chaves_resolvidas.update(chaves)

        return [
            CATALOGO_RELATORIOS[chave]
            for chave in chaves_resolvidas
            if chave in CATALOGO_RELATORIOS
        ]

    async def listar_profissionais(
        self,
        session: AsyncSession,
        busca: str | None = None,
        pagina: int = 1,
        tamanho: int = 10,
    ) -> dict[str, Any]:
        """Consulta paginada de profissionais inteligente com offset e limit."""
        filtro_sql = "AND UPPER(p.no_profissional) LIKE UPPER(:busca)" if busca else ""
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

            # Formata usando o schema ou dicionário
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
        """Obtém o perfil inteligente de um único profissional pelo ID."""
        sql = """
            WITH producao_cbo AS (
                SELECT co_dim_profissional AS id_prof, co_dim_cbo AS id_cbo, 'Procedimento' AS origem FROM tb_fat_proced_atend
                UNION
                SELECT co_dim_profissional, co_dim_cbo, 'Visita Domiciliar' FROM tb_fat_visita_domiciliar
                UNION
                SELECT co_dim_profissional_1, co_dim_cbo_1, 'Atendimento Individual' FROM tb_fat_atendimento_individual
                UNION
                SELECT co_dim_profissional_1, co_dim_cbo_1, 'Atendimento Odonto' FROM tb_fat_atendimento_odonto
                UNION
                SELECT co_dim_profissional, co_dim_cbo, 'Cadastro' FROM tb_fat_cad_individual
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

    # --- Método da Matriz Consolidada ---
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
                SELECT f.co_dim_profissional AS id_prof, t.nu_mes, 'Procedimentos' AS categoria
                FROM tb_fat_proced_atend f
                JOIN dim_tempo_filtrada t ON t.co_seq_dim_tempo = f.co_dim_tempo
                WHERE f.co_dim_profissional = :id_prof

                UNION ALL
                SELECT f.co_dim_profissional, t.nu_mes, 'Visita Domiciliar'
                FROM tb_fat_visita_domiciliar f
                JOIN dim_tempo_filtrada t ON t.co_seq_dim_tempo = f.co_dim_tempo
                WHERE f.co_dim_profissional = :id_prof

                UNION ALL
                SELECT f.co_dim_profissional_1, t.nu_mes, 'Atendimento Individual'
                FROM tb_fat_atendimento_individual f
                JOIN dim_tempo_filtrada t ON t.co_seq_dim_tempo = f.co_dim_tempo
                WHERE f.co_dim_profissional_1 = :id_prof

                UNION ALL
                SELECT f.co_dim_profissional_1, t.nu_mes, 'Atendimento Odontológico'
                FROM tb_fat_atendimento_odonto f
                JOIN dim_tempo_filtrada t ON t.co_seq_dim_tempo = f.co_dim_tempo
                WHERE f.co_dim_profissional_1 = :id_prof

                UNION ALL
                SELECT f.co_dim_profissional_1, t.nu_mes, 'Atendimento Domiciliar'
                FROM tb_fat_atendimento_domiciliar f
                JOIN dim_tempo_filtrada t ON t.co_seq_dim_tempo = f.co_dim_tempo
                WHERE f.co_dim_profissional_1 = :id_prof

                UNION ALL
                SELECT f.co_dim_profissional, t.nu_mes, 'Cadastro Individual'
                FROM tb_fat_cad_individual f
                JOIN dim_tempo_filtrada t ON t.co_seq_dim_tempo = f.co_dim_tempo
                WHERE f.co_dim_profissional = :id_prof

                UNION ALL
                SELECT f.co_dim_profissional, t.nu_mes, 'Cadastro Domiciliar'
                FROM tb_fat_cad_domiciliar f
                JOIN dim_tempo_filtrada t ON t.co_seq_dim_tempo = f.co_dim_tempo
                WHERE f.co_dim_profissional = :id_prof

                UNION ALL
                SELECT f.co_dim_profissional, t.nu_mes, 'Vacinação'
                FROM tb_fat_vacinacao f
                JOIN dim_tempo_filtrada t ON t.co_seq_dim_tempo = f.co_dim_tempo
                WHERE f.co_dim_profissional = :id_prof

                UNION ALL
                SELECT f.co_dim_profissional, t.nu_mes, 'Atividade Coletiva'
                FROM tb_fat_atividade_coletiva f
                JOIN dim_tempo_filtrada t ON t.co_seq_dim_tempo = f.co_dim_tempo
                WHERE f.co_dim_profissional = :id_prof

                UNION ALL
                SELECT f.co_dim_profissional, t.nu_mes, 'Consumo Alimentar'
                FROM tb_fat_marca_consumo_alimnt f
                JOIN dim_tempo_filtrada t ON t.co_seq_dim_tempo = f.co_dim_tempo
                WHERE f.co_dim_profissional = :id_prof

                UNION ALL
                SELECT f.co_dim_profissional_1, t.nu_mes, 'Avaliação de Elegibilidade'
                FROM tb_fat_avaliacao_elegibilidade f
                JOIN dim_tempo_filtrada t ON t.co_seq_dim_tempo = f.co_dim_tempo
                WHERE f.co_dim_profissional_1 = :id_prof
            ),
            pivoteado AS (
                SELECT 
                    categoria,
                    COUNT(CASE WHEN nu_mes = 1 THEN 1 END) AS "jan",
                    COUNT(CASE WHEN nu_mes = 2 THEN 1 END) AS "fev",
                    COUNT(CASE WHEN nu_mes = 3 THEN 1 END) AS "mar",
                    COUNT(CASE WHEN nu_mes = 4 THEN 1 END) AS "abr",
                    COUNT(CASE WHEN nu_mes = 5 THEN 1 END) AS "mai",
                    COUNT(CASE WHEN nu_mes = 6 THEN 1 END) AS "jun",
                    COUNT(CASE WHEN nu_mes = 7 THEN 1 END) AS "jul",
                    COUNT(CASE WHEN nu_mes = 8 THEN 1 END) AS "ago",
                    COUNT(CASE WHEN nu_mes = 9 THEN 1 END) AS "set",
                    COUNT(CASE WHEN nu_mes = 10 THEN 1 END) AS "out",
                    COUNT(CASE WHEN nu_mes = 11 THEN 1 END) AS "nov",
                    COUNT(CASE WHEN nu_mes = 12 THEN 1 END) AS "dez"
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
            SELECT 
                c.categoria,
                {colunas_soma}
            FROM categorias_oficiais c
            LEFT JOIN pivoteado p ON p.categoria = c.categoria
            GROUP BY c.categoria
            ORDER BY c.categoria;
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


service = RelatoriosService()
