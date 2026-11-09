import html
import re
from pathlib import Path
from urllib.parse import quote

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "templates"

XSS_PAYLOADS = [
    "<script>alert(1)</script>",
    "<img src=x onerror=alert(1)>",
    '<svg onload="alert(1)">x</svg>',
    """' " & < > á ç ã""",
]


@pytest.mark.parametrize("payload", XSS_PAYLOADS)
def test_page_parameters_are_rendered_as_escaped_text(
    client: TestClient, payload: str
) -> None:
    escaped_payload = (
        html.escape(payload, quote=True)
        .replace("&quot;", "&#34;")
        .replace("&#x27;", "&#39;")
    )
    encoded_payload = quote(payload, safe="")
    dashboard = client.get(f"/dashboard/123?nome={encoded_payload}")
    fallback_report = client.get(
        f"/relatorio/123?tipo={encoded_payload}&nome={encoded_payload}"
    )

    assert dashboard.status_code == 200
    assert fallback_report.status_code == 200
    assert escaped_payload in dashboard.text
    assert escaped_payload in fallback_report.text
    assert payload not in dashboard.text
    assert payload not in fallback_report.text


@pytest.mark.parametrize(
    ("template_name", "untrusted_fields", "safe_renderings"),
    [
        (
            "busca.html",
            ("${prof.nome}", "${prof.grupos[0]}"),
            ("nomeProfissional.textContent = prof.nome", "grupoTag.textContent ="),
        ),
        (
            "relatorio_visitas.html",
            ("${item.desfecho}", "${i.nome}"),
            (
                "celulaDesfecho.textContent = item.desfecho",
                "nomeItem.textContent = i.nome",
            ),
        ),
        (
            "relatorio_procedimentos.html",
            ("${s.procedimento}",),
            ("[s.procedimento,", "td.textContent = valor"),
        ),
        (
            "relatorio_procedimentos_odonto.html",
            ("${item.procedimento}",),
            (
                "nomeProcedimento.textContent = item.procedimento",
                "codigoProcedimento.textContent =",
            ),
        ),
        (
            "relatorio_consultas_medicas.html",
            (
                "${c.codigo_cid}",
                "${c.doenca}",
                "${ci.codigo_ciap}",
                "${ci.descricao}",
                "${p.codigo_procedimento}",
                "${p.nome_procedimento}",
            ),
            (
                "document.createTextNode(c.doenca)",
                "[ci.descricao,",
                "[p.nome_procedimento,",
            ),
        ),
        (
            "dashboard.html",
            ("${rel.titulo}",),
            (
                "titulo.textContent = rel.titulo",
                "nomeProfissional = {{ nome_profissional | tojson }}",
            ),
        ),
        (
            "relatorio_matriz.html",
            ("${linha.categoria}", "${dados.resumo.categoria}"),
            ("linha.categoria", "celula.textContent = valor"),
        ),
        (
            "relatorio_cadastros.html",
            ("${valor}",),
            ("valorCard.textContent = valor", "rotulo.textContent = label"),
        ),
        (
            "relatorio_consultas_odonto.html",
            ("${valor}", "${label}"),
            ("quantidade.textContent = valor", "nome.textContent = label"),
        ),
        (
            "relatorio_executivo.html",
            ("${dados.diretriz}", "${dados.resultado.msg}"),
            (
                "dados.diretriz",
                "dados.resultado.msg",
                "`📊 Evidência Bruta: ${dados.numeros}`",
            ),
        ),
    ],
)
def test_database_text_is_rendered_without_html_interpolation(
    template_name: str,
    untrusted_fields: tuple[str, ...],
    safe_renderings: tuple[str, ...],
) -> None:
    source = (TEMPLATES / template_name).read_text(encoding="utf-8")

    for interpolation in untrusted_fields:
        assert interpolation not in source
    for safe_rendering in safe_renderings:
        assert safe_rendering in source

    assert not re.search(
        r"\.innerHTML\s*\+?=\s*`[^`]*\$\{(?:prof\.nome|item\.desfecho|"
        r"i\.nome|s\.procedimento|item\.procedimento|c\.doenca|ci\.descricao|"
        r"p\.nome_procedimento)",
        source,
        flags=re.DOTALL,
    )
