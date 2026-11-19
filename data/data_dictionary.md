# Dicionário de Dados

## 1. Visão geral

| Item | Descrição |
|------|-----------|
| **Título** | Emissões de gases de efeito estufa (GEE) da cidade do Rio de Janeiro por escopo, segundo a metodologia GPC, 2012 a 2024 |
| **Fonte original** | Instituto Municipal de Urbanismo Pereira Passos (IPP) / Prefeitura do Rio de Janeiro, via portal [Data.Rio](https://www.data.rio), Tabela 3696 |
| **Arquivo bruto** | `data/raw/3696.xls` (aba utilizada: `3696_Escopos`) |
| **Arquivo processado** | `data/processed/emissoes_gee_rj_limpo.csv.gz` (CSV, UTF-8, separador vírgula, ponto decimal, compactado com gzip) |
| **Gerado por** | `src/etl.py` |
| **Granularidade** | Uma linha por **ano × setor × escopo** (13 anos × 39 setores × 4 escopos = 2.028 linhas) |
| **Cobertura temporal** | 2012 a 2024 (anual) |
| **Cobertura espacial** | Município do Rio de Janeiro (RJ, Brasil) |
| **Gases** | CO₂, CH₄ e N₂O, convertidos em CO₂ equivalente com os GWP do AR5 do IPCC |
| **Licença** | Dados derivados: CC BY 4.0 (ver `LICENSE-DATA.md`); dados originais: termos do Data.Rio/IPP |

## 2. Variáveis

| Variável | Significado | Tipo | Formato / domínio | Exemplo |
|----------|-------------|------|-------------------|---------|
| `ano` | Ano de referência do inventário | inteiro | `2012` a `2024` | `2024` |
| `macrossetor` | Categoria de 1º nível do GPC à qual a linha pertence. Vazio para a linha `TOTAL` e para itens informativos | texto (categórico) | 5 valores (seção 4) ou vazio | `Transportes` |
| `setor` | Nome do setor/subsetor emissor (rótulo da fonte, com pequenas correções ortográficas; ver seção 5) | texto | 39 valores distintos | `Rodoviário` |
| `nivel` | Posição da linha na hierarquia da tabela | texto (categórico) | `total`, `macrossetor`, `subsetor`, `item_informativo` (seção 3) | `subsetor` |
| `escopo` | Escopo da emissão segundo o GPC | texto (categórico) | `Escopo 1`, `Escopo 2`, `Escopo 3`, `Total` | `Escopo 1` |
| `emissao_tCO2e` | Emissão em toneladas de CO₂ equivalente. **Pode ser negativa** (remoções) e **vazia** (dado indisponível) | decimal (float64) | tCO₂e; ponto decimal | `4465253.8` |
| `qualidade_dado` | Origem/semântica do valor em `emissao_tCO2e` | texto (categórico) | seção 3 | `valor` |

### Escopos (GPC)

- **Escopo 1:** emissões diretas, de fontes localizadas dentro dos limites do município.
- **Escopo 2:** emissões indiretas pelo consumo de eletricidade da rede, geradas fora do município.
- **Escopo 3:** demais emissões indiretas que ocorrem fora do município por atividades realizadas nele.
- **Total:** soma dos três escopos (valor fornecido pela fonte).

## 3. Domínios das variáveis categóricas

### `nivel`

| Valor | Descrição | Entra na soma do total? |
|-------|-----------|-------------------------|
| `total` | Linha `TOTAL` oficial da fonte (uma por ano × escopo) | É o total |
| `macrossetor` | 5 categorias de 1º nível | Sim (soma = total) |
| `subsetor` | 31 subcategorias de cada macrossetor | **Não**, pois já estão contidos nos macrossetores |
| `item_informativo` | 2 linhas que, segundo a nota 2 da fonte, "fazem parte do conjunto de emissões territoriais mas não somam no total" | **Não** |

> **Nunca some todas as linhas.** Somar `macrossetor` + `subsetor` duplica as emissões (razão de exatamente 2,00 em todos os anos). Para totais, use `nivel == "total"`. Para composição, use **um único** nível.

### `qualidade_dado`

| Valor | Símbolo na fonte | Significado | `emissao_tCO2e` |
|-------|------------------|-------------|-----------------|
| `valor` | número | Valor numérico informado | número |
| `zero` | `-` | Zero **não** resultante de arredondamento | `0.0` |
| `zero_arredondado` | `(0)` | Zero resultante de arredondamento (não ocorre nesta versão da tabela) | `0.0` |
| `nao_disponivel` | `...` ou célula vazia | Dado não aplicável ou não disponível | **vazio (NaN)** |
| `nao_estimado` | `NE` | Não estimado (símbolo ausente das notas da fonte; interpretação dos autores) | **vazio (NaN)** |

Contagem na versão atual: `valor` = 1.334 · `nao_disponivel` = 557 · `zero` = 132 · `nao_estimado` = 5.

## 4. Hierarquia de setores

| Macrossetor | Subsetores |
|-------------|-----------|
| **Energia Estacionária** | Residencial · Comercial · Institucional · Iluminação Pública · Indústrias de manufatura e construção · Indústrias de energia · Agropecuário · Perdas comerciais de energia elétrica + outros não categorizados · Emissões fugitivas do setor de óleo e gás |
| **Transportes** | Rodoviário · Ferroviário · Aquaviário · Aéreo |
| **Resíduos** | Aterramento · Compostagem · Incineração e Queima a Céu Aberto · Esgotos e efluentes |
| **Processos Industriais e Uso de Produtos** | Produção de vidro · Produção de ferro e aço · Uso de lubrificantes e parafinas · Uso de óxido nitroso |
| **Agropecuária, Floresta e Uso do Solo** | Fermentação entérica · Manejo de dejetos · Reflorestamento · Arborização urbana · Mudança de uso do solo · Calagem · Aplicação de ureia · Emissões diretas de N₂O do manejo de solos · Emissões indiretas de N₂O do manejo de solos · Emissões indiretas de N₂O do manejo de dejetos |

Itens informativos (`nivel = item_informativo`): *Geração de energia elétrica para o Sistema Interligado Nacional (fora do total)* e *Compostagem (fora do total)*.

## 5. Tratamentos aplicados (rastreabilidade)

| # | Tratamento | Justificativa |
|---|-----------|---------------|
| 1 | Anos reconstruídos por *forward fill* (células mescladas no cabeçalho) | O ano aparece só na primeira coluna de cada bloco de escopos |
| 2 | Conversão de *wide* para *long* | Facilita agregações e gráficos |
| 3 | Criação de `nivel` e `macrossetor` a partir da posição das linhas | A planilha expressa a hierarquia apenas pela ordem das linhas |
| 4 | Símbolos `-`, `(0)`, `...`, `NE` convertidos conforme a seção 3, **sem imputação** | Distinguir zero de ausência; nenhum valor é inventado |
| 5 | Remoção de linhas de cabeçalho, fonte e notas de rodapé | Não são dados |
| 6 | Marcadores de nota (ex.: `(2)`) removidos dos rótulos; itens informativos recebem o sufixo ` (fora do total)` | Evita colisão de nomes (existem `Compostagem` subsetor e `Compostagem (2)` informativo) |
| 7 | Correção ortográfica: `Ferrroviário` → `Ferroviário`; `Incineração e Queima à Ceu Aberto` → `Incineração e Queima a Céu Aberto` | Erros de digitação na fonte |
| 8 | Validação automática: soma dos macrossetores = `TOTAL` (tolerância de 0,5%) | Detectar erros de leitura |

## 6. Observações e limitações

- **Valores negativos** (52 registros, em *Arborização urbana* e *Reflorestamento*) são **remoções** de carbono, e não erros.
- A fonte informa que os resultados de 2012 a 2021 foram **revisados em 2024**; os dados refletem a versão vigente.
- Os valores de `emissao_tCO2e` são estimativas de inventário, não medições diretas.
- `Escopo 2` e `Escopo 3` aparecem como `nao_disponivel` nos setores em que esses escopos não se aplicam.
