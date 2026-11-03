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

## 🛠️ Como Executar Localmente

1. Clone o repositório:
   ```bash
   git clone [https://github.com/NISPPTA/api-relatorios-esus-pec.git](https://github.com/NISPPTA/api-relatorios-esus-pec.git)
   cd api-relatorios-esus-pec