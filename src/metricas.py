"""Agregações, métricas descritivas e figuras da análise exploratória.

Todas as funções recebem o DataFrame longo gerado por ``src/etl.py``.
Regra central: o total anual vem da linha TOTAL oficial da fonte; somar
macrossetores *e* subsetores duplicaria as emissões (hierarquia do GPC).
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

BASE = Path(__file__).resolve().parent.parent
CSV = BASE / "data" / "processed" / "emissoes_gee_rj_limpo.csv.gz"
ASSETS = BASE / "docs" / "assets"

CORES_ESCOPO = {"Escopo 1": "#1f3a5f", "Escopo 2": "#2a9d8f", "Escopo 3": "#e9c46a"}
CORES_SETOR = {"Residencial": "#c8553d", "Comercial": "#3d7ea6"}
MEGA = 1e6  # t -> Mt


def carregar(caminho: str | Path = CSV) -> pd.DataFrame:
    return pd.read_csv(caminho)


# ---------- agregações ----------
def total_por_ano(df: pd.DataFrame) -> pd.Series:
    """RQ1: emissão total anual (t CO2e), linha TOTAL oficial."""
    f = df[(df.nivel == "total") & (df.escopo == "Total")]
    return f.set_index("ano")["emissao_tCO2e"]


def escopos_por_ano(df: pd.DataFrame) -> pd.DataFrame:
    """RQ1: emissões por escopo (colunas) e ano (linhas), linha TOTAL oficial."""
    f = df[(df.nivel == "total") & (df.escopo != "Total")]
    return f.pivot(index="ano", columns="escopo", values="emissao_tCO2e")


def escopo1_por_macrossetor(df: pd.DataFrame) -> pd.DataFrame:
    """RQ2: Escopo 1 por macrossetor (colunas) e ano (linhas)."""
    f = df[(df.nivel == "macrossetor") & (df.escopo == "Escopo 1")]
    return f.pivot(index="ano", columns="setor", values="emissao_tCO2e")


def top_subsetores_escopo1(df: pd.DataFrame, ano: int | None = None, n: int = 5) -> pd.DataFrame:
    """RQ2: maiores subsetores em Escopo 1 (um ano ou acumulado 2012 a 2024), com % do Escopo 1 total."""
    f = df[(df.nivel == "subsetor") & (df.escopo == "Escopo 1")]
    total = df[(df.nivel == "total") & (df.escopo == "Escopo 1")]
    if ano is not None:
        f, total = f[f.ano == ano], total[total.ano == ano]
    soma = f.groupby(["setor", "macrossetor"])["emissao_tCO2e"].sum().nlargest(n).reset_index()
    soma["pct_escopo1"] = 100 * soma["emissao_tCO2e"] / total["emissao_tCO2e"].sum()
    return soma


def escopo2_subsetores(df: pd.DataFrame) -> pd.DataFrame:
    """RQ3: Escopo 2 por subsetor de Energia Estacionária (colunas) e ano (linhas)."""
    f = df[(df.nivel == "subsetor") & (df.escopo == "Escopo 2") & (df.macrossetor == "Energia Estacionária")]
    return f.pivot(index="ano", columns="setor", values="emissao_tCO2e").fillna(0.0)


def participacao_escopo2(df: pd.DataFrame) -> pd.DataFrame:
    """RQ3: participação (%) de Residencial e Comercial no Escopo 2 total do município."""
    total = df[(df.nivel == "total") & (df.escopo == "Escopo 2")].set_index("ano")["emissao_tCO2e"]
    sub = escopo2_subsetores(df)[["Residencial", "Comercial"]]
    return sub.div(total, axis=0).mul(100).rename(columns=lambda c: f"{c} (%)")


# ---------- métricas descritivas ----------
def resumo_descritivo(serie: pd.Series) -> dict:
    """Tendência central, dispersão e extremos de uma série anual."""
    return {
        "media": serie.mean(),
        "desvio_padrao": serie.std(),
        "coef_variacao_pct": 100 * serie.std() / serie.mean(),
        "minimo": (int(serie.idxmin()), serie.min()),
        "maximo": (int(serie.idxmax()), serie.max()),
        "var_primeiro_ultimo_pct": 100 * (serie.iloc[-1] / serie.iloc[0] - 1),
    }


def concentracao(participacoes: pd.Series, k: int = 2) -> float:
    """Soma (%) das k maiores participações: medida simples de concentração."""
    return participacoes.nlargest(k).sum()


# ---------- figuras estáticas ----------
def _salvar(fig, nome: str) -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)
    fig.savefig(ASSETS / nome, dpi=200, bbox_inches="tight")


def fig_rq1(df: pd.DataFrame):
    esc, tot = escopos_por_ano(df) / MEGA, total_por_ano(df) / MEGA
    fig, ax = plt.subplots(figsize=(10, 5))
    base = pd.Series(0.0, index=esc.index)
    for col in esc.columns:
        ax.bar(esc.index, esc[col], bottom=base, label=col, color=CORES_ESCOPO[col], width=0.7)
        base += esc[col]
    ax.plot(tot.index, tot.values, color="#222", marker="o", lw=1.8, label="Total")
    for ano in (tot.idxmax(), tot.idxmin()):
        ax.annotate(f"{tot[ano]:.1f}", (ano, tot[ano]), textcoords="offset points",
                    xytext=(0, 8), ha="center", fontsize=10, fontweight="bold")
    ax.set(title="Emissões de GEE do município do Rio de Janeiro, por escopo (2012 a 2024)",
           xlabel="Ano", ylabel="Milhões de t CO₂e", xticks=tot.index)
    ax.legend(ncol=4, frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.12))
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    _salvar(fig, "rq1_evolucao_temporal.png")
    return fig


def fig_rq2(df: pd.DataFrame):
    mac = escopo1_por_macrossetor(df) / MEGA
    top = top_subsetores_escopo1(df, ano=2024)
    fig, (a, b) = plt.subplots(1, 2, figsize=(13, 5), gridspec_kw={"width_ratios": [1.2, 1]})
    mac = mac[mac.loc[2024].sort_values(ascending=False).index]
    paleta = ["#1f3a5f", "#3d7ea6", "#2a9d8f", "#e9c46a", "#999999"]
    base = pd.Series(0.0, index=mac.index)
    for cor, col in zip(paleta, mac.columns):
        a.bar(mac.index, mac[col], bottom=base, label=col, color=cor, width=0.7)
        base += mac[col]
    a.set(title="(a) Escopo 1 por macrossetor", xlabel="Ano", ylabel="Milhões de t CO₂e", xticks=mac.index[::2])
    a.legend(fontsize=8, frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=2)
    b.barh(top["setor"][::-1], top["pct_escopo1"][::-1], color="#1f3a5f")
    for y, v in enumerate(top["pct_escopo1"][::-1]):
        b.text(v + 0.5, y, f"{v:.1f}%", va="center", fontsize=9)
    b.set(title="(b) Cinco maiores subsetores em 2024", xlabel="% do Escopo 1 do município")
    b.set_xlim(0, top["pct_escopo1"].max() * 1.15)
    for ax in (a, b):
        ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    _salvar(fig, "rq2_ofensores_escopo1.png")
    return fig


def fig_rq3(df: pd.DataFrame):
    sub = escopo2_subsetores(df)[["Residencial", "Comercial"]] / 1e3
    part = participacao_escopo2(df)
    fig, (a, b) = plt.subplots(1, 2, figsize=(13, 4.8))
    for col in sub.columns:
        a.plot(sub.index, sub[col], marker="s", lw=2, label=col, color=CORES_SETOR[col])
    a.set(title="(a) Emissões de Escopo 2", xlabel="Ano", ylabel="Mil t CO₂e", xticks=sub.index[::2])
    a.legend(frameon=False)
    for col in part.columns:
        b.plot(part.index, part[col], marker="o", lw=2, label=col.replace(" (%)", ""),
               color=CORES_SETOR[col.replace(" (%)", "")])
    b.set(title="(b) Participação no Escopo 2 do município", xlabel="Ano", ylabel="% do Escopo 2 total",
          xticks=part.index[::2])
    b.set_ylim(0, 40)  # eixo iniciado em zero: não exagera variações pequenas
    b.legend(frameon=False)
    for ax in (a, b):
        ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    _salvar(fig, "rq3_matriz_energetica.png")
    return fig


# ---------- exportação para o artigo web (Plotly.js) ----------
def exportar_dados_web(df: pd.DataFrame, destino: Path = ASSETS) -> dict:
    """Gera docs/assets/dados_graficos.json e .js (para o artigo interativo)."""
    mac = escopo1_por_macrossetor(df)
    sub2 = escopo2_subsetores(df)
    dados = {
        "anos": [int(a) for a in total_por_ano(df).index],
        "total": total_por_ano(df).round(0).tolist(),
        "escopos": {c: escopos_por_ano(df)[c].round(0).tolist() for c in escopos_por_ano(df).columns},
        "escopo1_macrossetores": {c: mac[c].round(0).tolist() for c in mac.columns},
        "escopo2_subsetores": {c: sub2[c].round(0).tolist() for c in sub2.columns if sub2[c].sum() > 0},
        "escopo2_total": df[(df.nivel == "total") & (df.escopo == "Escopo 2")]["emissao_tCO2e"].round(0).tolist(),
    }
    destino.mkdir(parents=True, exist_ok=True)
    texto = json.dumps(dados, ensure_ascii=False)
    (destino / "dados_graficos.json").write_text(texto, encoding="utf-8")
    (destino / "dados_graficos.js").write_text(f"window.DADOS = {texto};\n", encoding="utf-8")
    return dados
