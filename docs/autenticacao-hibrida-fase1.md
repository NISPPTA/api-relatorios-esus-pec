# Especificacao tecnica — identidade e dados para autenticacao hibrida

Status: implementacao da Fase 1, sujeita a revisao humana antes de qualquer fase
posterior.

## Contexto e fatos do repositorio

- `src/main.py` cria o FastAPI, registra as paginas HTML, monta `/static`, configura
  CORS e inclui o router de relatorios.
- `src/db/database.py` cria uma engine SQLAlchemy assincrona e fornece uma sessao
  por requisicao. A configuracao atual nao separa uma credencial de runtime de uma
  credencial de migration.
- `src/modules/relatorios/router.py` injeta apenas a sessao de banco; as rotas ainda
  nao possuem autenticacao nem autorizacao.
- `src/modules/relatorios/service.py` implementa consultas textuais sobre as
  estruturas existentes do e-SUS PEC.
- Nao havia modelos de identidade, migrations Alembic ou especificacao tecnica
  versionada no repositorio. Este documento passa a ser a referencia versionada.
- O repositorio nao comprova schemas, grants, proprietarios ou roles configurados
  no Neon. Esses fatos devem ser verificados em ambiente controlado.

## Decisoes arquiteturais de base

- Uma pessoa possui uma conta interna; identidades de diferentes provedores
  apontam para essa conta.
- Login local usa Argon2id quando a Fase 2 for autorizada.
- GOV.BR e um provedor futuro, desabilitado ate aprovacao institucional,
  elegibilidade confirmada e credenciais oficiais.
- Ambos os provedores deverao convergir para uma sessao propria, opaca e persistida
  no PostgreSQL; token GOV.BR nao e sessao permanente.
- Vinculacao de identidade exige verificacao e auditoria. Nome ou e-mail iguais
  nunca bastam para associar contas.
- Nenhuma migration ou operacao de autenticacao pode modificar, excluir ou
  recriar estruturas oficiais do e-SUS PEC.
- Esta fase cria apenas modelos, migration, suporte a HMAC versionado e testes.
  Nao implementa login, bootstrap operacional, sessoes ativas ou protecao de
  rotas.

## Schema e privacidade

O schema reservado e `app_auth`. A migration nao cria o schema: ele deve ser
provisionado previamente por um operador de banco, com `app_migrator` como
proprietario. O Alembic recusa executar se o schema nao existir ou se a role da
migration nao for sua proprietaria.

O Alembic usa metadata que contem somente tabelas `app_auth`, filtra schemas e
tabelas para `app_auth` e armazena `alembic_version` no mesmo schema. Cada
operacao da migration e explicitamente qualificada com esse schema. Nenhum
`create_all`, introspeccao de autogeracao ou migration e executado no startup da
API.

### Roles e grants a provisionar externamente

Os seguintes requisitos sao um contrato de operacao, nao grants aplicados por
esta fase:

- `app_runtime`: role sem propriedade de objetos e sem `CREATE` no banco/schema.
  Recebe `USAGE` em `app_auth` e grants DML explicitamente selecionados por tabela
  quando os fluxos correspondentes forem implementados. A leitura das tabelas
  e-SUS deve ser somente `SELECT` nas tabelas necessarias aos relatorios; nao
  conceder `INSERT`, `UPDATE`, `DELETE`, `TRUNCATE`, `ALTER` ou propriedade nelas.
- `app_runtime` e `app_migrator` devem ser `NOINHERIT`, nao ter memberships em
  outras roles nem membros que possam assumir essas roles, e nao possuir
  privilegio `CREATE` no banco. O processo de migration rejeita qualquer uma
  dessas condicoes, assim como ownership ou escrita fora de `app_auth`.
- `app_migrator`: credencial separada e sem uso pela API. Deve ser proprietaria do
  schema `app_auth` e dos objetos criados nele, mas sem grants ou propriedade em
  schemas/tabelas oficiais, sem superuser, `CREATEDB` ou `CREATEROLE`. A migration
  verifica o nome/ownership do schema e flags dessas roles antes do DDL.
- `app_migrator` precisa de `CONNECT` ao banco e propriedade de `app_auth`
  previamente criada. A role de runtime nao recebe ownership nem DDL.
- A migration revoga acesso PUBLIC somente no schema/tabelas `app_auth`, concede
  `USAGE` e `SELECT` ao runtime e escritura explicitamente por tabela. Auditoria
  recebe `INSERT`, sem `UPDATE`/`DELETE`; roles e permissoes recebem somente
  `SELECT`; escrita em sessoes/limites fica restrita as tabelas necessarias. UUIDs
  nao exigem sequences.
- `app_roles`, `app_role_permissions` e `app_system_controls` permanecem
  somente leitura para `app_runtime`. Antes de implementar administracao de
  papeis ou bootstrap operacional, aprovar um caminho DML separado e restrito
  (por exemplo, uma credencial operacional sem DDL) ou revisar explicitamente
  esses grants; a credencial `app_migrator` nao deve ser usada pela API.
- Privilegios padrao do `app_migrator` concedem somente `SELECT` em futuras
  tabelas de `app_auth`; cada migration futura deve declarar explicitamente os
  grants de escrita necessarios. `app_migrator` deve existir e `app_runtime`
  precisa existir antes da migration; se nao, ela falha.
- O downgrade revoga os grants da role runtime em tabelas e no schema `app_auth`
  que foram concedidos pela migration. Ele mantem o schema pre-provisionado e a
  tabela `alembic_version`; nao recria privilegios `PUBLIC` nem afeta schemas
  externos.
- Os grants de escrita no schema da aplicacao nao devem ser confundidos com
  autorizacao de negocio. A Fase 2 precisara de servicos e dependencias que
  validem o ator antes de cada operacao.

Um proprietario de objetos mantem poderes inerentes de alteracao e exclusao;
revogar `ALTER` ou `DROP` nao remove esses poderes. Por isso, a role de migration
e deliberadamente proprietaria somente do schema/objetos `app_auth`, enquanto a
role de runtime nao e proprietaria de nenhum deles. Grants padrao nao mudam a
propriedade de objetos.

Antes de qualquer ambiente implantado, provisionar e testar roles/schema num
PostgreSQL descartavel. Verificar `pg_namespace`, `pg_class`, `pg_roles`,
`has_schema_privilege` e `has_table_privilege`; provar que migration/runtime nao
conseguem DDL ou DML de escrita em tabelas oficiais sinteticas. O Neon atual nao
foi consultado e nao se presume que esteja de acordo.

Se schema proprio for inviavel, alternativa sujeita a aprovacao: manter nomes
`app_*` no schema dedicado existente, limitar Alembic a essa allowlist e aplicar
os mesmos owners/grants tabela a tabela. Nao executar migrations em schema
compartilhado sem revisao humana do plano e dos grants.

## Modelo de dados

Todas as FKs entre entidades de autenticacao permanecem dentro de `app_auth`.
`professional_id` e `cnes` sao identificadores externos sem FK para o schema
oficial.

| Tabela | Finalidade e integridade |
|---|---|
| `app_users` | Conta interna UUID, estado `active/disabled`, timestamps e desativacao logica. Nao guarda credenciais ou identidade externa. |
| `app_auth_identities` | Vincula usuario a provedor (`local`/`govbr`) e issuer. Unicidade por usuario/provedor/issuer; nao armazena subject bruto. `local` usa issuer interno reservado `local`. |
| `app_auth_identity_keys` | Aliases de subject GOV.BR: HMAC-SHA256, versao positiva, issuer e identidade. Unicidade global do par provedor/issuer/versao/digest e FK composta para assegurar que provider/issuer pertencem a identidade. |
| `app_local_credentials` | Identidade local e identificador de login normalizado unico, campo reservado ao hash Argon2id. FK composta exige que a identidade seja local. Nenhuma credencial e criada nesta fase. |
| `app_sessions` | Hash SHA-256 do token, usuario, expiracao absoluta/inativa e revogacao. Hash com tamanho verificado e token unico. A tabela nao ativa sessao por si so. |
| `app_roles` | Catalogo de papeis. Nenhum papel ou administrador e semeado. |
| `app_user_roles` | Concessoes com ator, fonte, datas, revogacao e referencia formal quando a concessao inicial vier de bootstrap. Indice parcial impede duplicar concessao nao revogada. |
| `app_role_permissions` | Permissoes de papel com escopo `global`, `report`, `professional` ou `unit`. Permissao por relatorio e representada por escopo `report` e identificador do catalogo. |
| `app_user_permission_grants` | Concessao excepcional direta: permissao, escopo, justificativa nao vazia, concessor, inicio, expiracao obrigatoria e revogacao. Expiracao deve ser posterior ao inicio; nenhuma linha e semeada. |
| `app_user_professionals` | Vinculo temporal usuario/profissional, com concedente. ID deve ser positivo; sem FK para o banco oficial. |
| `app_user_units` | Vinculo temporal usuario/CNES, com concedente; formato numerico de ate sete digitos. Sem FK ao banco oficial. |
| `app_login_attempts` | Bucket persistente para futuro rate limit; digests HMAC versionados de identificador e origem, janela, contador e bloqueio. Nenhum identificador bruto. |
| `app_audit_logs` | Eventos minimos, ator/resultado/alvo/escopo e dados operacionais. Bootstrap pode ter ator `bootstrap_operators` e `actor_user_id` nulo. Constraints exigem operadores, referencia formal e conta alvo no evento de bootstrap. |
| `app_system_controls` | Linha singleton `singleton_id=1` criada como `pending`. Estado concluido exige instante, identidade administrativa, operadores institucionais, referencia de autorizacao e resultado. FKs apontam para `app_users`. |

O estado singleton permite que a futura rotina use transacao e
`SELECT ... FOR UPDATE`, depois valide `pending`, crie usuario/identidade/role,
registre auditoria e mude o controle para `completed` atomicamente. A chave
primaria e `CHECK (singleton_id = 1)` impedem uma segunda linha; o lock serializa
execucoes concorrentes. A operacao nao e implementada nem executada nesta fase.
Uma falha antes do commit nao deve deixar conta parcial; registro de tentativa
fracassada deve usar caminho de auditoria separado e nunca conter credenciais.

### Separacao de administracao e dados clinicos

Codigos em avaliacao: `manage_users`, `manage_roles`, `manage_scopes`,
`view_reports`, `view_all_reports` e `view_sensitive_aggregates`. Esta migration
nao cria papeis, permissoes ou atribuicoes.

Administrar contas, papéis e escopos nao implica visualizar relatorios. `admin`
nao recebe `view_all_reports` nem `view_sensitive_aggregates` automaticamente.
Concessao excepcional requer permissao especifica, escopo, justificativa,
concessor, inicio, expiracao e possibilidade de revogacao, com auditoria de ator,
justificativa, data, escopo e resultado. A futura autorizacao deve consultar
concessoes no banco em cada requisicao ou usar mecanismo que garanta revogacao
imediata; a recomendacao e nao manter cache de autorizacao. GOV.BR, login local
ou CBO nao concedem privilegios.

## HMAC e rotacao

HMAC nao e cifra e nao pode ser revertido. As chaves sao dedicadas, versionadas e
guardadas fora do banco e do repositorio; qualquer chave de cifra e independente.
O helper da Fase 1 calcula HMAC-SHA256 de issuer/subject GOV.BR sem persistir o
subject e resolve uma identidade somente se todos os aliases encontrados
concordarem.

Rotacao futura:

1. Distribuir a chave nova versionada por mecanismo de segredo aprovado e manter
   a antiga ativa durante a transicao.
2. Em uma assercao GOV.BR valida, calcular aliases para as versoes aceitas,
   localizar a identidade e adicionar o digest novo na mesma transacao.
3. Unicidade do banco e escrita concorrente devem impedir identidade duplicada;
   conflitos de aliases diferentes falham fechados e geram alerta sem dados
   sensiveis.
4. Confirmar cobertura da versao nova e resolver conflitos antes de desativar a
   versao antiga. Rollback reativa lookup pela chave anterior, sem apagar aliases
   novos.
5. Se o subject original nao estiver disponivel, HMAC antigo nao permite
   recalculo: exigir nova autenticacao valida ou revinculacao controlada. Nao
   guardar CPF bruto para evitar esse trabalho sem necessidade formal aprovada.
6. Falta de chave impede autenticacao dependente dela. Nao criar identidade de
   fallback.

Custodia, acesso, backup e recuperacao das chaves precisam de aprovacao
institucional. O helper nao carrega chaves do ambiente, arquivo ou banco; isso
sera tratado em fase posterior.

## Bootstrap do primeiro administrador

Quando autorizado numa fase futura, o bootstrap sera um comando operacional
explicito, nunca startup ou rota HTTP. Exige procedimento institucional,
operadores identificados e referencia formal. A credencial sera recebida por
prompt sem eco ou canal operacional aprovado; nunca por argumento de linha de
comando, log, Git ou valor padrao.

O comando devera usar transacao serializada no singleton, falhar em reexecucao,
criar somente a conta/identidade/papel administrativo minimo e registrar
operadores, referencia, horario, identidade criada e resultado. Como nao existe
administrador previo, ator interno sera nulo e tipo do ator sera
`bootstrap_operators`; nao inventar um concedente. Nenhum hash ou segredo sera
registrado. Recuperacao administrativa exige procedimento institucional
controlado, auditoria e revogacao de sessoes.

Esta fase apenas prepara as constraints/tabelas; nao cria conta, role, credencial
nem executa comando de bootstrap.

## Autenticacao e autorizacao futuras

### Local

Login local futuro: Argon2id, conta provisionada sem cadastro publico, rate limit
persistente, resposta generica, sessao propria e revogacao de sessoes apos reset
de senha/desativacao. Fluxo de login, hashing, cookies, CSRF e recuperacao nao
fazem parte da Fase 1.

### GOV.BR

GOV.BR permanece desabilitado. Apenas apos aprovacao e documentacao oficial:
fluxo de autorizacao/callback, state/nonce, validacao de assinatura, issuer,
audience, exp, PKCE se suportado/exigido, protecao contra replay, credenciais em
secret store e validacao de atributos/consentimento. Nao se presumem endpoints,
scopes, claims ou identificadores. Sucesso resolve identidade ja vinculada e
cria sessao local; tokens GOV.BR nao se tornam sessao permanente.

### Rotas existentes

Nenhuma rota e protegida nesta Fase 1. Na fase de autorizacao, proteger tanto as
paginas quanto as APIs:

| Metodo/caminho | Autorizacao futura |
|---|---|
| `GET /` | Redirecionamento sem dados; pode ser publico. |
| `GET /busca` | Sessao; busca limitada por papel e escopo. |
| `GET /dashboard/{id_profissional}` | Sessao e autorizacao do profissional. |
| `GET /relatorio/{id_profissional}` | Sessao, escopo e permissao do relatorio. |
| `GET /api/relatorios/profissionais` | Sessao; escopo aplicado antes da listagem, contagem e pagina. |
| `GET /api/relatorios/profissionais/{id_profissional}/perfil` | Sessao e escopo do profissional. |
| `GET /api/relatorios/profissionais/{id_profissional}/matriz-producao` | Sessao, permissao do relatorio e escopo. |
| `GET /api/relatorios/profissionais/{id_profissional}/visitas` | Sessao, permissao territorial e escopo. |
| `GET /api/relatorios/profissionais/{id_profissional}/procedimentos` | Sessao, permissao e escopo. |
| `GET /api/relatorios/profissionais/{id_profissional}/cadastros-territorio` | Sessao, permissao territorial e escopo. |
| `GET /api/relatorios/profissionais/{id_profissional}/relatorio-executivo` | Sessao, permissao de gestao explicita e escopo. |
| `GET /api/relatorios/profissionais/{id_profissional}/consultas-odonto` | Sessao, permissao e escopo. |
| `GET /api/relatorios/profissionais/{id_profissional}/procedimentos-odonto` | Sessao, permissao e escopo. |
| `GET /api/relatorios/profissionais/{id_profissional}/lotacoes` | Sessao; limitar profissionais e unidades retornadas. |
| `GET /api/relatorios/profissionais/{id_profissional}/consultas-medicas` | Sessao, permissao, profissional e cada CNES autorizado. |
| `/docs`, `/redoc`, `/openapi.json` | Desabilitar em producao ou restringir. |
| `/static/*` | Publico somente se os arquivos forem nao sensiveis. |

Para IDOR/BOLA, a autorizacao precisa chegar as consultas SQL. Gestor limitado a
unidades nao pode obter outras unidades trocando `id_profissional`, `cnes` ou
omitindo o CNES. Escopo deve ser aplicado antes de agregacao, contagem,
ordenacao, filtro e paginacao. O frontend, iframe, CBO e a autenticacao de
qualquer provedor nao sao controles de acesso.

## HTTP e operacao

CORS atual permite origens/metodos/headers wildcard com credenciais em
`src/main.py`. Antes de cookies, restringir a origem real, preferir same-origin e
definir metodos/headers minimos. Cookies futuros: `HttpOnly`, `Secure`,
`SameSite=Lax`, `Path=/`, sem `Domain`; avaliar `__Host-`. Operacoes mutaveis
precisarao CSRF e validacao de Origin. HSTS/headers devem considerar TLS e proxy
do Render; CSP precisa preservar JavaScript inline e iframe durante migracao
gradual. Documentacao FastAPI deve ser desabilitada/restrita em producao.

## Testes e verificacoes

Testes unitarios sem banco verificam metadata, FKs, unicidade/check constraints,
separacao de provedores/credenciais/permissoes, ausencia de usuarios/papeis
semeados e calculo/resolucao de aliases HMAC em varias versoes.

Testes PostgreSQL sao opt-in usando somente URL de banco descartavel explicitamente
configurada, com nome que identifique ambiente de teste e confirmacao explicita.
Nunca usar `DATABASE_URL`, `.env`, Neon ou uma URL inferida. O alvo deve estar
provisionado com roles de migration/runtime e schema de teste.

Cobertura de integracao:

- Upgrade cria somente objetos `app_auth`; tabela oficial sintetica permanece
  identica.
- Runtime nao e proprietario, nao tem DDL em `app_auth` nem escrita em tabela
  oficial; migration role nao possui tabela/schema oficial.
- Falhas de grants resultam em erro e nao sao contornadas.
- FKs e unicidade rejeitam duplicatas de identidade por provedor/issuer/versao.
- Aliases antigos e novos resolvem a mesma identidade; aliases conflitantes
  falham fechados.
- `app_system_controls` admite uma unica linha; lock transacional impede duas
  conclusoes concorrentes.
- Concessao excepcional exige ator, escopo, justificativa e expiracao; expiracao
  e revogacao sao refletidas na consulta de autorizacao sem cache persistente.
- Migration sobe, desce e pode subir novamente no banco descartavel. Downgrade
  remove dados de autenticacao do schema proprio; nao deve ser usado como
  rollback de producao sem backup/aprovacao.

No ambiente de desenvolvimento atual nao ha executavel local de PostgreSQL,
`psql`, `initdb` ou Docker encontrado. A suite de integracao PostgreSQL so podera
ser considerada aprovada quando executada num ambiente isolado apropriado.

## Plano e limite desta entrega

1. **Identidade/dados (esta fase):** modelos, migration restrita a `app_auth`,
   documento de grants, helper HMAC e testes de schema/alias. Sem auth runtime,
   usuarios ou chamadas ao Neon.
2. **Sessoes e provedor local:** Argon2id, login/logout, cookie, CSRF, rate limit,
   bootstrap operacional e sessao persistida.
3. **Autorizacao de rotas:** dependencias e restricoes SQL para todas as paginas
   e endpoints.
4. **Interface de login:** templates e fluxos same-origin.
5. **GOV.BR:** somente apos autorizacao e homologacao oficial.
6. **Auditoria e producao:** validacao de grants, testes, operacao, rollback e
   deploy controlado.

Fase 2 ou posterior exige revisao e autorizacao explicita do responsavel.

## Pendencias institucionais e tecnicas

- Identificador local, provisionamento, recuperacao e se havera contas GOV.BR-only.
- Papeis, relatorios, escopos, acesso excepcional e revisao periodica.
- Caminho de privilégio DML mínimo para bootstrap e manutenção do catálogo de
  papéis sem expor a credencial proprietária de migrations.
- Operadores, aprovacao formal, custodia e contingencia do primeiro administrador.
- Elegibilidade, issuer, subject, scopes, claims, consentimento e credenciais
  oficiais GOV.BR.
- Permissoes reais do Neon, possibilidade de schema/roles separados, migrations,
  backup e chave HMAC/criptografia.
- Dominios, TLS, proxies, CORS e cookies no Render.
- Retencao de sessoes, tentativas e auditoria.
