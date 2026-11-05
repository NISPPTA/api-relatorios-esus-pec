# 📊 API de Relatórios - e-SUS PEC

API em FastAPI para espelhamento e geração de relatórios de produção do e-SUS PEC.

Este projeto resolve o desafio de consolidar métricas de produção da Atenção Primária à Saúde (como procedimentos individualizados, visitas domiciliares e cadastros), lidando com as inconsistências de nomenclatura e duplicidade de IDs inerentes ao esquema do banco oficial do SUS.

## 🚀 Tecnologias Utilizadas

- **Linguagem:** Python 3.13
- **Framework Web:** FastAPI
- **ORM:** SQLAlchemy 2.0 (Assíncrono)
- **Banco de Dados:** PostgreSQL (Hospedado no Neon)
- **Driver de Conexão:** `asyncpg`
- **Gerencienciador de Dependências:** Poetry

## ⚙️ Arquitetura e Funcionalidades

A aplicação foi desenhada de forma modular (`Configuração`, `Banco de Dados`, `Regras de Negócio` e `Rotas`) para garantir escalabilidade.

- **Pivoteamento Dinâmico em Memória:** As queries extraem os dados brutos via `COUNT(1)` diretamente das Tabelas de Fatos (`tb_fat_...`), e o backend em Python realiza o pivoteamento das colunas de meses de forma dinâmica, aliviando a carga do banco de dados.
- **Espelhamento Oficial:** A matriz de saída garante a presença das 12 categorias oficiais do relatório de Série Histórica do PEC, preenchendo os meses sem produção com zeros automaticamente.
- **Consultas Blindadas:** Uso de parâmetros SQL estritos para evitar injeções e adaptação aos nomes exatos de colunas mapeadas via `information_schema` (ex: `co_dim_profissional` vs `co_dim_profissional_1`).


# API Relatórios e-SUS PEC - Painel Gerencial SUS

Plataforma analítica e de conformidade desenvolvida para extrair, cruzar e auditar dados do e-SUS PEC (Prontuário Eletrônico do Cidadão). O sistema transforma dados brutos de produção da Atenção Primária à Saúde em inteligência gerencial, garantindo auditoria legal, autenticidade visual e alinhamento às diretrizes do Ministério da Saúde (PNAB, Previne Brasil).

## 🚀 Arquitetura e Tecnologias
- **Back-end:** Python, FastAPI, SQLAlchemy (Async).
- **Front-end:** HTML5, Tailwind CSS, JavaScript Vanilla, Chart.js, Jinja2 Templates.
- **Padrões Técnicos:** Nomenclatura oficial PT-BR (Ministério da Saúde), formatação inspirada em ABNT, sistema de "chancela" (marca d'água de autenticidade) para exportação em PDF.

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

## 📅 Histórico de Desenvolvimento: Sprint 2 - Saúde Bucal

A segunda etapa focou em mapear a produção odontológica (Cirurgião Dentista, ASB e TSB), alinhando os dados brutos aos indicadores do Previne Brasil e blocos de financiamento, com encerramento homologado em **05 de Novembro de 2026**.

| Período / Fase | Assunto e Requisitos Levantados | Implementação Realizada |
| :--- | :--- | :--- |
| **Fase 1:**<br>Levantamento de Dados | Necessidade de extrair a produção clínica odontológica e procedimentos SIGTAP. Cruzamento das tabelas `tb_fat_atendimento_odonto` e `tb_fat_atend_odonto_proced`. | Criação de queries agrupando consultas (vigilância bucal, insumos, encaminhamentos) e totalização de procedimentos realizados na cadeira odontológica. |
| **Fase 2:**<br>Saneamento (Data Sanitization) | Desafio de inconsistências e nomenclaturas redundantes no PEC (ex: códigos internos `ABPG` vs `SIGTAP` para o mesmo procedimento de remoção de sutura). | Refatoração no backend para unificar descrições idênticas em memória, concatenando os códigos (garantindo rastreabilidade para auditoria) e reduzindo a poluição visual. |
| **Fase 3:**<br>Classificação Semântica | Categorizar a lista de procedimentos brutos em blocos clínicos legíveis para a gestão. | Implementação de filtros Python por palavras-chave (ex: *SELANTE, PULPOTOMIA, DRENAGEM*) roteando dados para as categorias de Prevenção, Cirurgia, Endodontia, etc. |
| **Fase 4:**<br>UI/UX e Impressão | Necessidade de visualização gerencial limpa, tratamento de ausência de dados e PDFs sem quebras abruptas de tabelas. | Criação dos templates `relatorio_consultas_odonto.html` e `relatorio_procedimentos_odonto.html` com cores semânticas Tailwind, tratamento de *Empty States* via JS e CSS `@media print` (`break-inside: avoid`). |
| **Fase 5:**<br>Roteamento Dinâmico | Ocultar relatórios territoriais (ACS) para perfis clínicos (Dentistas) e vice-versa, priorizando a usabilidade. | Atualização do `dashboard.html` para consumir o endpoint de Perfil via API, renderizando a Sidebar dinamicamente com base nas permissões do CBO do profissional em tela. |

---

## 📊 Módulos Entregues (CBO: Saúde Bucal)

1. **Consultas e Tratamentos Odontológicos:** 
   - **KPIs:** Total de Atendimentos, Tratamentos Concluídos (% de resolutividade), Gestantes Atendidas (Previne Brasil) e Retornos Agendados.
   - **Métricas:** Vigilância em Saúde Bucal (rastreio de dor, abscesso, traumas), Fornecimento de Insumos e Encaminhamentos CEO (Endodontia, Bucomaxilo, etc.).
2. **Procedimentos Odontológicos Especializados (SIGTAP):**
   - Catálogo inteligente e saneado com contagem precisa de **Tipos Distintos Executados**.
   - Categorização clínica automática em blocos coloridos: *Prevenção e Atenção Básica, Dentística Restauradora, Periodontia, Cirurgia e Exodontias, Endodontia e Outros Procedimentos*.

---

## 🚀 Sprint Atual (Em Andamento)
- **Sprint 3: Módulo Clínico/Ambulatorial (Médico e Enfermeiro)**
  * Linhas de cuidado de doenças crônicas (Hipertensão/Diabetes).
  * Saúde da Mulher (Citopatológico), Puericultura e Vacinograma.

## 🔜 Próximos Passos (Backlog)
- **Sprint 4:** Ações Coletivas e Equipe Multiprofissional (eMulti).