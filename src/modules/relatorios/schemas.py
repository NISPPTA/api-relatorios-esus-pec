from pydantic import BaseModel, Field


class RelatorioDisponivel(BaseModel):
    """
    Contrato que define a estrutura de um relatório disponível no catálogo do sistema.
    """

    id: str = Field(
        ...,
        example="visitas_domiciliares",
        description="Identificador único do relatório.",
    )
    titulo: str = Field(
        ...,
        example="Relatório Analítico de Visitas Domiciliares",
        description="Título de exibição na interface.",
    )
    descricao: str = Field(
        ...,
        example="Desfechos de visita, motivos e busca ativa",
        description="Breve explicação sobre os dados contidos no relatório.",
    )
    categoria: str = Field(
        ...,
        example="Territorial",
        description="Agrupamento macro do relatório (ex: Territorial, Clínico, Odonto).",
    )
    endpoint_relatorio: str = Field(
        ...,
        example="/api/relatorios/profissionais/{id_profissional}/visitas",
        description="Caminho da API para consumir os dados do relatório.",
    )


class ProfissionalPerfil(BaseModel):
    """
    Contrato que define o perfil consolidado de um profissional, incluindo
    os seus grupos, frentes de atuação e relatórios aos quais tem acesso.
    """

    id_profissional: int = Field(
        ...,
        example=229,
        description="ID sequencial do profissional no banco do e-SUS PEC.",
    )
    nome: str = Field(
        ...,
        example="Angela Roberta Fernandes Carlos de Lacerda",
        description="Nome completo do profissional.",
    )
    grupos: list[str] = Field(
        ...,
        example=["AUXILIAR OU TÉCNICO DE ENFERMAGEM"],
        description="Lista de perfis de CBO identificados.",
    )
    frentes_atuacao: list[str] = Field(
        ...,
        example=["Procedimento", "Vacinação"],
        description="Módulos do sistema onde o profissional registou produção.",
    )
    relatorios_habilitados: list[RelatorioDisponivel] = Field(
        ...,
        description="Lista de relatórios dinamicamente liberados com base nos grupos do profissional.",
    )
