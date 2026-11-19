"""ETL do inventário de emissões de GEE da cidade do Rio de Janeiro (Data.Rio, tabela 3696).

Transforma a planilha original (formato wide, cabeçalho em dois níveis) em uma
tabela longa e rastreável, salva em ``data/processed/emissoes_gee_rj_limpo.csv.gz``.

Uso:
    python src/etl.py
    python src/etl.py --entrada caminho/3696.xls --saida caminho/saida.csv.gz
"""
from __future__ import annotations

import argparse
import re
import warnings
from pathlib import Path

import numpy as np

try:
    import pandas as pd
except ModuleNotFoundError as exc:  # pragma: no cover
    raise SystemExit(
        "Dependências faltando. Instale-as com: python -m pip install -r requirements.txt"
    ) from exc

warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")

ABA = "3696_Escopos"

# Categorias de 1º nível do GPC; as linhas seguintes são seus subsetores.
MACROSSETORES = (
    "Energia Estacionária",
    "Transportes",
    "Resíduos",
    "Processos Industriais e Uso de Produtos",
    "Agropecuária, Floresta e Uso do Solo",
)

# Símbolos da fonte (notas 4 a 6 da planilha). "NE" não consta nas notas;
# é interpretado como "não estimado".
SIMBOLOS = {
    "-": (0.0, "zero"),                 # zero não resultante de arredondamento
    "(0)": (0.0, "zero_arredondado"),   # zero resultante de arredondamento
    "...": (np.nan, "nao_disponivel"),  # não aplicável ou não disponível
    "NE": (np.nan, "nao_estimado"),
}

# Correções ortográficas de rótulos (a planilha original não é alterada).
CORRECOES_ROTULOS = {
    "Ferrroviário": "Ferroviário",
    "Incineração e Queima à Ceu Aberto": "Incineração e Queima a Céu Aberto",
}

COLUNAS_SAIDA = [
    "ano", "macrossetor", "setor", "nivel", "escopo", "emissao_tCO2e", "qualidade_dado",
]


def _limpar_rotulo(valor: str) -> str:
    """Remove espaços extras e marcadores de nota, como '(2)', do rótulo."""
    texto = re.sub(r"\s*\(\d\)\s*$", "", str(valor).strip())
    texto = re.sub(r"\s+", " ", texto)
    return CORRECOES_ROTULOS.get(texto, texto)


def _converter_valor(valor) -> tuple[float, str]:
    """Converte uma célula em (valor numérico, qualidade) sem perder a semântica da fonte."""
    if isinstance(valor, str):
        chave = valor.strip()
        if chave in SIMBOLOS:
            return SIMBOLOS[chave]
        numero = pd.to_numeric(chave.replace(",", "."), errors="coerce")
        return (float(numero), "valor") if pd.notna(numero) else (np.nan, "nao_disponivel")
    if valor is None or pd.isna(valor):
        return np.nan, "nao_disponivel"
    return float(valor), "valor"


def extrair(caminho: str | Path) -> pd.DataFrame:
    """Lê a aba de escopos da planilha bruta, sem cabeçalho (extração)."""
    print(f"[*] Lendo o arquivo bruto: {caminho}")
    return pd.read_excel(caminho, sheet_name=ABA, header=None)


def transformar(bruto: pd.DataFrame) -> pd.DataFrame:
    """Converte o formato wide (ano x escopo em colunas) em longo e classifica a hierarquia."""
    linha_nome = bruto.index[bruto.iloc[:, 0].astype(str).str.strip() == "Nome"]
    if len(linha_nome) != 1:
        raise ValueError("Cabeçalho 'Nome' não encontrado (ou duplicado) na planilha.")
    i_ano = linha_nome[0]
    i_escopo = i_ano + 1

    anos = bruto.iloc[i_ano, 1:].ffill()  # o ano aparece só na 1ª coluna de cada bloco mesclado
    escopos = bruto.iloc[i_escopo, 1:].astype(str).str.strip()
    colunas = [(int(float(a)), e) for a, e in zip(anos, escopos)]

    registros = []
    total_visto = False
    macro_atual = None
    for _, linha in bruto.iloc[i_escopo + 1:].iterrows():
        rotulo = linha.iloc[0]
        if pd.isna(rotulo):
            if registros:  # a primeira linha vazia após os dados encerra a tabela
                break
            continue  # linha em branco entre o cabeçalho e os dados
        setor = _limpar_rotulo(rotulo)

        if setor.upper() == "TOTAL":
            nivel, macro, total_visto, setor = "total", None, True, "TOTAL"
        elif total_visto:
            # Itens após o TOTAL "fazem parte do conjunto de emissões territoriais
            # mas não somam no total" (nota 2 da fonte).
            nivel, macro = "item_informativo", None
            setor = f"{setor} (fora do total)"  # evita colisão, ex.: 'Compostagem'
        elif setor in MACROSSETORES:
            nivel, macro = "macrossetor", setor
            macro_atual = setor
        else:
            nivel, macro = "subsetor", macro_atual

        for (ano, escopo), celula in zip(colunas, linha.iloc[1:]):
            valor, qualidade = _converter_valor(celula)
            registros.append((ano, macro, setor, nivel, escopo, valor, qualidade))

    df = pd.DataFrame(registros, columns=COLUNAS_SAIDA)
    df["ano"] = df["ano"].astype("int16")
    ordem = ["ano", "nivel", "macrossetor", "setor", "escopo"]
    return df.sort_values(ordem, kind="stable").reset_index(drop=True)


def validar(df: pd.DataFrame, tolerancia: float = 0.005) -> None:
    """Confere se a soma dos macrossetores reproduz o TOTAL oficial (consistência interna)."""
    total = df[df.nivel == "total"].set_index(["ano", "escopo"])["emissao_tCO2e"]
    soma = df[df.nivel == "macrossetor"].groupby(["ano", "escopo"])["emissao_tCO2e"].sum()
    pior = ((soma - total).abs() / total).dropna().max()
    print(f"[*] Validação: maior divergência macrossetores x TOTAL = {pior:.4%}")
    if pior > tolerancia:
        raise ValueError(f"Soma dos macrossetores diverge do TOTAL oficial em até {pior:.2%}.")


def carregar(caminho: str | Path) -> pd.DataFrame:
    """Executa extração, transformação e validação."""
    df = transformar(extrair(caminho))
    validar(df)
    return df


BASE = Path(__file__).resolve().parent.parent
ENTRADA_PADRAO = BASE / "data" / "raw" / "3696.xls"
SAIDA_PADRAO = BASE / "data" / "processed" / "emissoes_gee_rj_limpo.csv.gz"


def executar(entrada: str | Path = ENTRADA_PADRAO, saida: str | Path = SAIDA_PADRAO) -> pd.DataFrame:
    """Roda o pipeline completo e grava o CSV compactado. Pode ser chamada de um notebook."""
    entrada, saida = Path(entrada), Path(saida)
    if not entrada.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {entrada}")

    df = carregar(entrada)
    saida.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(saida, index=False, encoding="utf-8", compression="gzip")

    print(f"[*] Linhas: {len(df)} | anos: {df.ano.min()} a {df.ano.max()}")
    print(f"[*] Qualidade dos dados:\n{df.qualidade_dado.value_counts().to_string()}")
    print(f"[+] ETL concluído. Arquivo salvo em: {saida}")
    return df


def main() -> None:
    ap = argparse.ArgumentParser(description="ETL das emissões de GEE do Rio de Janeiro")
    ap.add_argument("--entrada", default=ENTRADA_PADRAO)
    ap.add_argument("--saida", default=SAIDA_PADRAO)
    args = ap.parse_args()
    try:
        executar(args.entrada, args.saida)
    except FileNotFoundError as exc:
        raise SystemExit(f"[!] {exc}")


if __name__ == "__main__":
    main()
