# Instrucoes de engenharia — api-relatorios-esus-pec

Estas instrucoes se aplicam a todo o trabalho neste repositorio. O objetivo e evoluir a aplicacao para producao sem quebrar os relatorios, os contratos existentes ou as regras de negocio do e-SUS PEC.

## Arquitetura encontrada

- `src/main.py` e o ponto de entrada: cria a aplicacao FastAPI, monta os templates e arquivos estaticos, declara as paginas HTML e inclui o router de relatorios. Nao presuma que exista um `main.py` na raiz.
- `src/db/database.py` carrega `DATABASE_URL` por `pydantic-settings`, cria uma engine SQLAlchemy assincrona e fornece sessoes por requisicao via `get_db_session`.
- `src/modules/relatorios/router.py` define as rotas HTTP, valida parte dos parametros com FastAPI e encaminha as operacoes ao servico.
- `src/modules/relatorios/service.py` concentra regras de negocio e consultas PostgreSQL. As consultas sao majoritariamente SQL textual executado por `AsyncSession`; nao ha camada de modelos ORM ou repositorios estabelecida.
- `src/modules/relatorios/schemas.py` contem modelos Pydantic para os contratos atualmente tipados. Nem todas as rotas declaram `response_model`.
- `templates/` contem paginas Jinja2 com JavaScript inline que consome a API. `src/main.py` serve `static/` em `/static`.
- `pyproject.toml` define Python `>=3.13,<3.14` e dependencias gerenciadas por Poetry. `tests/` contem a suite pytest; `djlint` e usado para verificacao de templates.

Antes de mudar uma area, confira os arquivos e o comportamento relacionados; nao infira tabelas, colunas, relacionamentos, regras ou requisitos do banco e-SUS PEC sem evidencia no codigo ou em documentacao confiavel do projeto.

## Principios de mudanca

- Preserve a arquitetura existente e prefira alteracoes pequenas, justificadas e compativeis com os templates e consumidores atuais.
- Nao reescreva funcionalidades que funcionam, remova relatorios, consultas, filtros ou regras de negocio sem requisito explicito e justificativa tecnica.
- Nao altere o schema ou os dados do banco. Qualquer proposta de migracao exige justificativa, plano de migracao e aprovacao; nunca execute mudancas destrutivas ou apague dados.
- Mantenha nomes, formatos, parametros, status HTTP e estruturas de resposta existentes, a menos que uma mudanca de contrato seja necessaria, documentada e compatibilizada.
- Nao trate menus, CBO ou controles da interface como autorizacao. Regras de acesso a dados devem ser aplicadas no backend.
- Nao introduza dependencias, abstracoes ou infraestrutura sem necessidade demonstrada. Nao desabilite verificacoes para obter uma execucao aparentemente aprovada.
- Não faça commits, pushes, merges ou alterações em
  branches sem autorização explícita.
- Preserve as alterações locais existentes do usuário.
- Antes de modificar arquivos, verifique se existem
  alterações não commitadas que possam ser afetadas.

## Backend, SQL e banco de dados

- Use `AsyncSession` e APIs assincronas do SQLAlchemy. Preserve uma sessao por requisicao e o fechamento garantido pela dependencia; nao guarde sessoes em estado global nem compartilhe uma mesma `AsyncSession` entre operacoes concorrentes.
- Parametrize todos os valores externos em consultas SQL usando bind parameters do SQLAlchemy (`text(...), {...}`). Nunca concatene entrada externa em SQL. Se identificadores ou fragmentos SQL precisarem ser dinamicos, derive-os somente de uma lista interna fixa e validada; parametros bind nao substituem validacao de identificadores.
- Ao alterar uma consulta, preserve a semantica de filtros, agregacoes, datas e contagens. Confirme tabelas e colunas no codigo ou em schema/documentacao autorizada; nao as invente.
- Valide entradas na camada HTTP com tipos, limites e schemas Pydantic adequados. Adicione `response_model` quando definir ou alterar contratos, preservando o formato usado pelos consumidores existentes.
- Trate erros de forma explicita: respostas externas devem ser estaveis e nao conter SQL, credenciais, stack traces ou detalhes internos; detalhes tecnicos devem ir para logs apropriados, sem dados pessoais desnecessarios.
- Considere limites de consulta, paginacao e consumo de memoria para conjuntos grandes. Nao carregue resultados sem limite quando a operacao puder crescer.
- Nao registre nem exponha `DATABASE_URL`, tokens, senhas, identificadores pessoais ou resultados clinicos. Leia somente nomes de variaveis de ambiente quando necessario; nunca abra, altere ou mostre arquivos `.env` ou outros arquivos de segredo.
- Não execute consultas exploratórias em massa no banco
  de produção. Antes de executar consultas potencialmente
  pesadas, avalie seu impacto e obtenha autorização.

## Seguranca e dados pessoais

- Trate dados de profissionais, producao e saude como dados pessoais e, quando aplicavel, sensiveis. Minimize coleta, exibicao, logs e retencao; aplique a LGPD e os controles de acesso existentes ou aprovados.
- Aplique autenticacao, autorizacao, validacao e limites no servidor. Nunca dependa exclusivamente de JavaScript, URLs ou filtros da interface para proteger dados.
- Preserve configuracoes seguras de CORS e headers ao altera-las; nao amplie origens, metodos ou headers sem necessidade e configuracao explicita para o ambiente.
- Nao introduza segredos em codigo, testes, fixtures, documentacao ou logs. Mantenha `.env` fora do versionamento e use mecanismos de configuracao/secrets apropriados ao ambiente.
- Evite SQL injection, XSS, redirecionamentos inseguros e exposicao de informacoes internas. Ao identificar um risco relacionado a mudanca, corrija-o ou descreva claramente o risco e a limitacao.
- Nunca utilize dados reais de pacientes em testes,
  exemplos, fixtures, logs ou capturas de tela.
  Utilize dados sintéticos e anonimizados.

## Jinja2, HTML e JavaScript

- Preserve os nomes dos templates, os parametros de contexto fornecidos por `src/main.py` e as URLs/formatos da API usados pelas paginas.
- Mantenha o escape automatico do Jinja2. Nao use `|safe`, `Markup` ou HTML confiavel para dados externos ou valores do banco.
- Trate qualquer valor da API, URL ou banco como nao confiavel. Prefira `textContent` e criacao de elementos DOM a interpolar valores em `innerHTML`; se HTML dinamico for indispensavel, sanitize com uma estrategia aprovada.
- Nao interpolar dados nao confiaveis diretamente em scripts inline. Para dados iniciais no HTML, use serializacao segura para JavaScript e valide no cliente; a validacao do cliente nao substitui a do servidor.
- Nao introduza dependencias externas de frontend ou altere o comportamento de cache/recursos sem avaliar CSP, integridade/origem, compatibilidade e impacto nos templates.

## Processo de desenvolvimento

Para cada mudanca:

1. Inspecione os arquivos envolvidos, os chamadores e os contratos consumidos por templates e clientes.
2. Identifique riscos, dependencias e compatibilidade; apresente um plano curto antes de uma alteracao nao trivial.
3. Implemente a menor mudanca completa e consistente com os padroes do projeto.
4. Adicione ou atualize testes em `tests/` para o comportamento alterado; use somente dados sinteticos e mantenha os testes independentes de bancos de producao.
5. Execute verificacoes relevantes e informe exatamente quais comandos rodaram, seus resultados e quaisquer limitacoes. Use `poetry run pytest` para testes, `poetry run djlint templates/ --check` para templates e `poetry run uvicorn src.main:app` para uma verificacao de inicializacao local; nao conecte a bancos de producao nem use credenciais reais em testes.
6. Revise regressao de contratos, consultas, filtros, templates e privacidade. Ao concluir, resuma arquivos alterados, verificacoes executadas e pendencias.

Nunca considere uma verificacao aprovada se ela nao foi executada. Nao masque erros, nao reporte sucesso em caso de falha e nao inclua valores secretos nos resultados.
