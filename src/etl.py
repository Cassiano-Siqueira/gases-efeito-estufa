from pathlib import Path
import pandas as pd

def extract_and_transform(file_path: str) -> pd.DataFrame:
    print(f"[*] A ler o ficheiro: {file_path}")
    dados = pd.read_excel(file_path, sheet_name='3696_Escopos', header=None, engine='xlrd')

    anos = dados.iloc[3, 1:].ffill().astype(str).str.replace('.0', '', regex=False)
    escopos = dados.iloc[4, 1:]
    cabecalhos = ['setor'] + [f"{ano}_{escopo}" for ano, escopo in zip(anos, escopos)]

    dados = dados.iloc[6:].copy()
    dados.columns = cabecalhos
    dados = dados.dropna(subset=['setor'])
    dados = dados[~dados['setor'].str.contains('Total', na=False, case=False)]

    dados = pd.melt(dados, id_vars='setor', var_name='ano_escopo', value_name='emissao_tCO2e')
    dados[['ano', 'escopo']] = dados['ano_escopo'].str.split('_', n=1, expand=True)
    dados = dados.drop(columns='ano_escopo')

    dados['ano'] = pd.to_numeric(dados['ano'], errors='coerce')
    dados['emissao_tCO2e'] = pd.to_numeric(dados['emissao_tCO2e'], errors='coerce').fillna(0.0)
    dados['setor'] = dados['setor'].astype(str).str.strip()

    return dados[['ano', 'setor', 'escopo', 'emissao_tCO2e']].sort_values(by=['ano', 'setor'])


def main():
    base_dir = Path(__file__).resolve().parent.parent
    raw_path = base_dir / 'data' / 'raw' / '3696.xls'
    processed_path = base_dir / 'data' / 'processed' / 'emissoes_gee_rj_limpo.csv'

    if not raw_path.exists():
        print(f"[!] Ficheiro não encontrado: {raw_path}")
        return

    processed_path.parent.mkdir(parents=True, exist_ok=True)
    df_clean = extract_and_transform(str(raw_path))
    print(f"[*] A guardar em: {processed_path}")
    df_clean.to_csv(processed_path, index=False, encoding='utf-8')
    print("[+] Concluído!")


if __name__ == '__main__':
    main()
