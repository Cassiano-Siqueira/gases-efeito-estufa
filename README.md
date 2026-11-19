# Emissões de Gases de Efeito Estufa no Rio de Janeiro

Projeto acadêmico de análise das emissões de gases de efeito estufa (GEE) da cidade do Rio de Janeiro. O projeto organiza os dados da planilha original, gera um arquivo CSV e apresenta uma análise exploratória.

## Estrutura

- `data/raw/3696.xls`: planilha original.
- `data/processed/emissoes_gee_rj_limpo.csv`: dados processados.
- `src/etl.py`: script que transforma a planilha em CSV.
- `notebooks/analise_exploratoria.ipynb`: análise dos dados.
- `docs/index.html`: página do projeto.

## Como executar

No terminal, na pasta do projeto:

```bash
python -m venv .venv
```

Ative o ambiente virtual e instale as dependências:

```bash
pip install -r requirements.txt
```

Execute o processamento:

```bash
python src/etl.py
```

O arquivo CSV processado será salvo em `data/processed/`.