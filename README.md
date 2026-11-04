# 📊 API de Relatórios - e-SUS PEC

API em FastAPI para espelhamento e geração de relatórios de produção do e-SUS PEC.

Este projeto resolve o desafio de consolidar métricas de produção da Atenção Primária à Saúde (como procedimentos individualizados, visitas domiciliares e cadastros), lidando com as inconsistências de nomenclatura e duplicidade de IDs inerentes ao esquema do banco oficial do SUS.

## 🚀 Tecnologias Utilizadas

* **Linguagem:** Python 3.13
* **Framework Web:** FastAPI
* **ORM:** SQLAlchemy 2.0 (Assíncrono)
* **Banco de Dados:** PostgreSQL (Hospedado no Neon)
* **Driver de Conexão:** `asyncpg`
* **Gerencienciador de Dependências:** Poetry

## ⚙️ Arquitetura e Funcionalidades

A aplicação foi desenhada de forma modular (`Configuração`, `Banco de Dados`, `Regras de Negócio` e `Rotas`) para garantir escalabilidade.

* **Pivoteamento Dinâmico em Memória:** As queries extraem os dados brutos via `COUNT(1)` diretamente das Tabelas de Fatos (`tb_fat_...`), e o backend em Python realiza o pivoteamento das colunas de meses de forma dinâmica, aliviando a carga do banco de dados.
* **Espelhamento Oficial:** A matriz de saída garante a presença das 12 categorias oficiais do relatório de Série Histórica do PEC, preenchendo os meses sem produção com zeros automaticamente.
* **Consultas Blindadas:** Uso de parâmetros SQL estritos para evitar injeções e adaptação aos nomes exatos de colunas mapeadas via `information_schema` (ex: `co_dim_profissional` vs `co_dim_profissional_1`).


# API Relatórios e-SUS PEC - Painel Gerencial SUS

Plataforma analítica e de conformidade desenvolvida para extrair, cruzar e auditar dados do e-SUS PEC (Prontuário Eletrônico do Cidadão). O sistema transforma dados brutos de produção da Atenção Primária à Saúde em inteligência gerencial, garantindo auditoria legal, autenticidade visual e alinhamento às diretrizes do Ministério da Saúde (PNAB, Previne Brasil).

## 🚀 Arquitetura e Tecnologias
* **Back-end:** Python, FastAPI, SQLAlchemy (Async).
* **Front-end:** HTML5, Tailwind CSS, JavaScript Vanilla, Chart.js, Jinja2 Templates.
* **Padrões Técnicos:** Nomenclatura oficial PT-BR (Ministério da Saúde), formatação inspirada em ABNT, sistema de "chancela" (marca d'água de autenticidade) para exportação em PDF.

---

## 📅 Histórico de Desenvolvimento: Sprint 1 - Agente Comunitário de Saúde (ACS)

A primeira etapa do projeto foi focada em mapear e auditar 100% do esforço de campo e território do Agente Comunitário de Saúde (ACS), culminando em um encerramento homologado em **04 de Novembro de 2026**.

| Período / Fase | Assunto e Requisitos Levantados | Implementação Realizada |
| :--- | :--- | :--- |
| **Fase 1:**<br>Fundação de Dados | Levantamento de métricas territoriais, perfil adscrito e esforço de visitas de campo. Necessidade de cruzar tabelas de produção SIGTAP e e-SUS. | Criação do `service.py` com queries complexas (SQL) integrando `tb_fat_cad_individual`, `tb_fat_cad_domiciliar` e `tb_fat_visita_domiciliar`. Criação da API REST. |
| **Fase 2:**<br>Relatórios Base | Transformar os JSONs da API em relatórios visuais imprimíveis e com alta escaneabilidade. | Desenvolvimento dos templates `relatorio_matriz.html`, `relatorio_cadastros.html` e `relatorio_visitas.html` com gráficos Chart.js e métricas brutas. |
| **Fase 3:**<br>Auditoria e Gestão | Necessidade de automatizar a auditoria do Ministério da Saúde, evitando cálculos manuais de conformidade da PNAB e Rede Cegonha. | Criação do Painel Executivo (`relatorio_executivo.html`) com semáforos (Verde, Amarelo, Vermelho). Cruzamento de dados de visitas vs. doenças crônicas e vulnerabilidade. |
| **Fase 4:**<br>UX e Navegação | Problema de usabilidade: a navegação entre relatórios exigia voltar à tela de busca constantemente. | Refatoração da busca (`busca.html`) e criação de um ambiente central unificado (`dashboard.html`) com Sidebar persistente e renderização via Iframe. |
| **Fase 5:**<br>Polimento e ABNT | Adequação de idioma (PT-BR), inserção de proporção gerencial (%) para análise de esforço e garantia de autenticidade documental. | Revisão ortográfica (Substituição de "doentes" por "pacientes"), adição de tooltips explicativos, marca d'água oficial no CSS e colunas fixas de porcentagem. |

---

## 📊 Módulos Entregues (CBO: ACS)

1. **Dashboard Centralizado:** Navegação fluida sem perda de contexto da pesquisa original.
2. **Matriz Consolidada de Série Histórica:** Visão temporal (mensal) de todos os registros (cadastros e visitas).
3. **Acompanhamento Territorial e Cadastros:** Mapeamento de famílias, demografia, condições crônicas (HAS/DM) e vulnerabilidades estruturais do território com peso percentual.
4. **Boletim Analítico de Visitas Domiciliares:** Desfechos de sucesso vs. recusas/ausências, distribuição de esforço de campo em gráficos de rosca e lista de ações priorizadas por porcentagem.
5. **Painel Executivo de Conformidade:** Síntese analítica cruzada. Gera alertas automáticos sobre cumprimento da meta de cobertura da PNAB, acompanhamento da Rede Cegonha e assistência de equidade a domiciliados.

---

## 🚀 Sprint Atual (Em Andamento)
* **Sprint 2: Saúde Bucal (Cirurgião Dentista, ASB, TSB)**
  * Consultas odontológicas e procedimentos especializados.
  * Efetividade de tratamentos concluídos, primeiras consultas programáticas e urgências bucais.

## 🔜 Próximos Passos (Backlog)
* **Sprint 3:** Implementação do módulo Clínico/Ambulatorial (Médico, Enfermeiro).
* **Sprint 4:** Ações Coletivas e Equipe Multiprofissional (eMulti).



## 🛠️ Como Executar Localmente

1. Clone o repositório:
   ```bash
   git clone [https://github.com/NISPPTA/api-relatorios-esus-pec.git](https://github.com/NISPPTA/api-relatorios-esus-pec.git)
   cd api-relatorios-esus-pec