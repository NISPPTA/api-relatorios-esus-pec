from pydantic import BaseModel, Field


class RelatorioDisponivel(BaseModel):
    id: str = Field(..., example="visitas_domiciliares")
    titulo: str = Field(..., example="Relatório Analítico de Visitas Domiciliares")
    descricao: str = Field(..., example="Desfechos de visita, motivos e busca ativa")
    categoria: str = Field(..., example="Territorial")
    endpoint_relatorio: str = Field(
        ..., example="/api/relatorios/profissionais/{id_profissional}/visitas"
    )


class ProfissionalPerfil(BaseModel):
    id_profissional: int = Field(..., example=229)
    nome: str = Field(..., example="Angela Roberta Fernandes Carlos de Lacerda")
    grupos: list[str] = Field(..., example=["AUXILIAR OU TÉCNICO DE ENFERMAGEM"])
    frentes_atuacao: list[str] = Field(..., example=["Procedimento"])
    relatorios_habilitados: list[RelatorioDisponivel]
