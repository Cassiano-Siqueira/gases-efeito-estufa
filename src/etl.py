from pathlib import Path
import warnings

try:
    import pandas as pd
except ModuleNotFoundError as exc:
    raise SystemExit(
        "Dependências faltando. Instale-as com: python -m pip install -r requirements.txt"
    ) from exc

# Suprimir avisos de formatação do Excel
warnings.filterwarnings('ignore', category=UserWarning, module='openpyxl')


def extract_and_transform(file_path: str) -> pd.DataFrame:
    """Extrai e higieniza os dados de emissões do Data.Rio."""
    print(f"[*] A ler o ficheiro bruto: {file_path}")

    # O ficheiro original possui formatação complexa nas primeiras linhas.
    # O Excel pode ser .xlsx (openpyxl) ou .xls (xlrd).
    excel_engine = 'xlrd' if str(file_path).lower().endswith('.xls') else 'openpyxl'
    df_raw = pd.read_excel(file_path, sheet_name='3696_Escopos', header=None, engine=excel_engine)

    # Os anos estão na linha 3 e cada ano abrange quatro colunas.
    anos = df_raw.iloc[3, 1:].ffill().astype(str).str.replace('.0', '', regex=False)

    # Os escopos estão na linha 4.
    escopos = df_raw.iloc[4, 1:]

    # Criar um novo cabeçalho combinado (ex: "2012_Escopo 1")
    novos_cabecalhos = ['setor'] + [f"{ano}_{escopo}" for ano, escopo in zip(anos, escopos)]

    # Isolar apenas a matriz de dados (a partir da linha 6, após linhas em branco)
    df_dados = df_raw.iloc[6:].copy()
    df_dados.columns = novos_cabecalhos

    # Remover linhas totalmente nulas ou de totais gerais
    df_dados = df_dados.dropna(subset=['setor'])
    df_dados['setor'] = df_dados['setor'].fillna('').astype(str)
    df_dados = df_dados[~df_dados['setor'].str.contains('Total', na=False, case=False)]

    print("[*] A aplicar 'Melt' (transformação para formato longo)...")
    # Derreter a tabela (Wide to Long)
    df_long = pd.melt(df_dados, id_vars=['setor'], var_name='ano_escopo', value_name='emissao_tCO2e')

    # Separar a coluna combinada 'ano_escopo' em 'ano' e 'escopo'
    df_long[['ano', 'escopo']] = df_long['ano_escopo'].str.split('_', n=1, expand=True)
    df_long.drop(columns=['ano_escopo'], inplace=True)

    # Limpeza final de tipos de dados
    df_long['ano'] = pd.to_numeric(df_long['ano'], errors='coerce')
    df_long['emissao_tCO2e'] = pd.to_numeric(df_long['emissao_tCO2e'], errors='coerce').fillna(0.0)
    df_long['setor'] = df_long['setor'].astype(str).str.strip()

    # Reordenar colunas
    df_final = df_long[['ano', 'setor', 'escopo', 'emissao_tCO2e']].sort_values(by=['ano', 'setor'])

    return df_final


def main():
    # Definir caminhos relativos
    base_dir = Path(__file__).resolve().parent.parent
    raw_path = base_dir / 'data' / 'raw' / '3696.xls'
    processed_path = base_dir / 'data' / 'processed' / 'emissoes_gee_rj_limpo.csv'

    if not raw_path.exists():
        print(f"[!] Erro: Ficheiro não encontrado em {raw_path}")
        return

    processed_path.parent.mkdir(parents=True, exist_ok=True)

    # Executar transformação
    df_clean = extract_and_transform(str(raw_path))

    print(f"[*] A guardar dados processados em: {processed_path}")
    df_clean.to_csv(processed_path, index=False, encoding='utf-8')
    print("[+] ETL concluído com sucesso!")


if __name__ == '__main__':
    main()s