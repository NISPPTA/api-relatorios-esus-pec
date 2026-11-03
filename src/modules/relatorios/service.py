# Aqui encapsulamos a nossa query mestre blindada e a lógica em Python que formata as colunas (pivoteamento dinâmico) para qualquer intervalo de datas.

from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class RelatorioProducaoService:
    async def gerar_matriz_producao_mensal(
        self,
        session: AsyncSession,
        profissional_id: int,
        ano: int,
        mes_inicio: int,
        mes_fim: int,
    ) -> list[dict[str, Any]]:
        """Gera a matriz de produção cruzando as 12 categorias oficiais do e-SUS PEC."""

        query = text("""
            WITH parametros AS (
                SELECT 
                    :id_profissional AS id_profissional,
                    :ano AS ano,
                    :mes_inicio AS mes_inicio,
                    :mes_fim AS mes_fim
            )
            SELECT 1 AS ordem_grupo, 'Cadastros' AS grupo, 'Cadastro domiciliar e territorial' AS descricao, t.nu_mes, COUNT(1) AS qtd
            FROM tb_fat_cad_domiciliar fd JOIN tb_dim_tempo t ON t.co_seq_dim_tempo = fd.co_dim_tempo CROSS JOIN parametros p
            WHERE fd.co_dim_profissional = p.id_profissional AND t.nu_ano = p.ano AND t.nu_mes BETWEEN p.mes_inicio AND p.mes_fim GROUP BY t.nu_mes
            UNION ALL
            SELECT 1, 'Cadastros', 'Cadastro individual', t.nu_mes, COUNT(1) 
            FROM tb_fat_cad_individual fi JOIN tb_dim_tempo t ON t.co_seq_dim_tempo = fi.co_dim_tempo CROSS JOIN parametros p
            WHERE fi.co_dim_profissional = p.id_profissional AND t.nu_ano = p.ano AND t.nu_mes BETWEEN p.mes_inicio AND p.mes_fim GROUP BY t.nu_mes
            UNION ALL
            SELECT 2, 'Produção', 'Atendimento domiciliar', t.nu_mes, COUNT(1) 
            FROM tb_fat_atendimento_domiciliar fad JOIN tb_dim_tempo t ON t.co_seq_dim_tempo = fad.co_dim_tempo CROSS JOIN parametros p
            WHERE fad.co_dim_profissional_1 = p.id_profissional AND t.nu_ano = p.ano AND t.nu_mes BETWEEN p.mes_inicio AND p.mes_fim GROUP BY t.nu_mes
            UNION ALL
            SELECT 2, 'Produção', 'Atendimento individual', t.nu_mes, COUNT(1) 
            FROM tb_fat_atendimento_individual fai JOIN tb_dim_tempo t ON t.co_seq_dim_tempo = fai.co_dim_tempo CROSS JOIN parametros p
            WHERE fai.co_dim_profissional_1 = p.id_profissional AND t.nu_ano = p.ano AND t.nu_mes BETWEEN p.mes_inicio AND p.mes_fim GROUP BY t.nu_mes
            UNION ALL
            SELECT 2, 'Produção', 'Atendimento odontológico individual', t.nu_mes, COUNT(1) 
            FROM tb_fat_atendimento_odonto fao JOIN tb_dim_tempo t ON t.co_seq_dim_tempo = fao.co_dim_tempo CROSS JOIN parametros p
            WHERE fao.co_dim_profissional_1 = p.id_profissional AND t.nu_ano = p.ano AND t.nu_mes BETWEEN p.mes_inicio AND p.mes_fim GROUP BY t.nu_mes
            UNION ALL
            SELECT 2, 'Produção', 'Atividade coletiva', t.nu_mes, COUNT(1) 
            FROM tb_fat_atividade_coletiva fac JOIN tb_dim_tempo t ON t.co_seq_dim_tempo = fac.co_dim_tempo CROSS JOIN parametros p
            WHERE fac.co_dim_profissional = p.id_profissional AND t.nu_ano = p.ano AND t.nu_mes BETWEEN p.mes_inicio AND p.mes_fim GROUP BY t.nu_mes
            UNION ALL
            SELECT 2, 'Produção', 'Avaliação de elegibilidade e admissão', t.nu_mes, COUNT(1) 
            FROM tb_fat_avaliacao_elegibilidade fea JOIN tb_dim_tempo t ON t.co_seq_dim_tempo = fea.co_dim_tempo CROSS JOIN parametros p
            WHERE fea.co_dim_profissional_1 = p.id_profissional AND t.nu_ano = p.ano AND t.nu_mes BETWEEN p.mes_inicio AND p.mes_fim GROUP BY t.nu_mes
            UNION ALL
            SELECT 2, 'Produção', 'Marcadores de consumo alimentar', t.nu_mes, COUNT(1) 
            FROM tb_fat_marca_consumo_alimnt fmc JOIN tb_dim_tempo t ON t.co_seq_dim_tempo = fmc.co_dim_tempo CROSS JOIN parametros p
            WHERE fmc.co_dim_profissional = p.id_profissional AND t.nu_ano = p.ano AND t.nu_mes BETWEEN p.mes_inicio AND p.mes_fim GROUP BY t.nu_mes
            UNION ALL
            SELECT 2, 'Produção', 'Procedimentos individualizados', t.nu_mes, COUNT(1) 
            FROM tb_fat_proced_atend fpa JOIN tb_dim_tempo t ON t.co_seq_dim_tempo = fpa.co_dim_tempo CROSS JOIN parametros p
            WHERE fpa.co_dim_profissional = p.id_profissional AND t.nu_ano = p.ano AND t.nu_mes BETWEEN p.mes_inicio AND p.mes_fim GROUP BY t.nu_mes
            UNION ALL
            SELECT 2, 'Produção', 'Síndrome neurológica por Zika / Microcefalia', t.nu_mes, 0 
            FROM tb_dim_tempo t CROSS JOIN parametros p
            WHERE t.nu_ano = p.ano AND t.nu_mes BETWEEN p.mes_inicio AND p.mes_fim GROUP BY t.nu_mes
            UNION ALL
            SELECT 2, 'Produção', 'Vacinação', t.nu_mes, COUNT(1) 
            FROM tb_fat_vacinacao fv JOIN tb_dim_tempo t ON t.co_seq_dim_tempo = fv.co_dim_tempo CROSS JOIN parametros p
            WHERE fv.co_dim_profissional = p.id_profissional AND t.nu_ano = p.ano AND t.nu_mes BETWEEN p.mes_inicio AND p.mes_fim GROUP BY t.nu_mes
            UNION ALL
            SELECT 2, 'Produção', 'Visita domiciliar e territorial', t.nu_mes, COUNT(1) 
            FROM tb_fat_visita_domiciliar vd JOIN tb_dim_tempo t ON t.co_seq_dim_tempo = vd.co_dim_tempo CROSS JOIN parametros p
            WHERE vd.co_dim_profissional = p.id_profissional AND t.nu_ano = p.ano AND t.nu_mes BETWEEN p.mes_inicio AND p.mes_fim GROUP BY t.nu_mes
        """)

        res_bruta = await session.execute(
            query,
            {
                "id_profissional": profissional_id,
                "ano": ano,
                "mes_inicio": mes_inicio,
                "mes_fim": mes_fim,
            },
        )
        dados_banco = res_bruta.all()

        # Estrutura base garantindo as 12 categorias na ordem oficial do relatório[cite: 7]
        matriz_base = [
            (1, "Cadastros", "Cadastro domiciliar e territorial"),
            (1, "Cadastros", "Cadastro individual"),
            (2, "Produção", "Atendimento domiciliar"),
            (2, "Produção", "Atendimento individual"),
            (2, "Produção", "Atendimento odontológico individual"),
            (2, "Produção", "Atividade coletiva"),
            (2, "Produção", "Avaliação de elegibilidade e admissão"),
            (2, "Produção", "Marcadores de consumo alimentar"),
            (2, "Produção", "Procedimentos individualizados"),
            (2, "Produção", "Síndrome neurológica por Zika / Microcefalia"),
            (2, "Produção", "Vacinação"),
            (2, "Produção", "Visita domiciliar e territorial"),
        ]

        # Criação dinâmica das colunas (ex: "05/2026")
        colunas_meses = [
            f"{str(m).zfill(2)}/{ano}" for m in range(mes_inicio, mes_fim + 1)
        ]
        relatorio_final = []

        for ordem, grupo, descricao in matriz_base:
            linha = {
                "grupo": grupo,
                "descricao": descricao,
            }
            # Preenche os meses e o total com 0
            for col in colunas_meses:
                linha[col] = 0
            linha["Total"] = 0
            relatorio_final.append(linha)

        # Atualiza a estrutura de memória (pivoteamento veloz sem forçar o banco)
        mapa_linhas = {item["descricao"]: item for item in relatorio_final}
        for row in dados_banco:
            coluna_mes = f"{str(row.nu_mes).zfill(2)}/{ano}"
            if (
                row.descricao in mapa_linhas
                and coluna_mes in mapa_linhas[row.descricao]
            ):
                mapa_linhas[row.descricao][coluna_mes] += row.qtd
                mapa_linhas[row.descricao]["Total"] += row.qtd

        return relatorio_final
