# Word Cloud - Priorização de Distritos por Necessidade

## 📋 Descrição

Este script gera uma **word cloud visual** que prioriza os distritos atendidos pelo projeto baseado em múltiplos indicadores de necessidade. A visualização ajuda a responder a pergunta:

> **"Com uma quantidade específica de cestas e mais famílias do que cestas disponíveis, qual distrito priorizar?"**

## 🎯 Objetivo

A word cloud mostra os distritos onde **o tamanho do nome** representa o **nível de necessidade**. Os distritos maiores são os mais prioritários para receber ajuda.

## 📦 Instalação

### Dependências Necessárias

```bash
pip install wordcloud matplotlib pandas numpy
```

Ou instale todas de uma vez:

```bash
pip install -r requirements_wordcloud.txt
```

## 🚀 Como Usar

1. Certifique-se de que os arquivos estão no lugar:
   - Arquivos `.txt` em `crawler/temp/curated/` e `crawler/temp/trusted/`
   - Dados consolidados em `Arquivos_Tratados/Consolidados/`
   - Dados de análise em `analysis/`

2. Execute o script:

```bash
python wordcloud_distritos.py
```

## 📊 Saída

O script gera dois arquivos:

1. **`analysis/wordcloud_distritos_priorizados.png`**
   - Imagem da word cloud visual
   - Tamanho da palavra = nível de necessidade
   - Inclui ranking na legenda

2. **`analysis/scores_priorizacao_distritos.csv`**
   - Tabela detalhada com todos os scores
   - Permite análise mais profunda dos dados

## 🧮 Método de Cálculo

O score de priorização é calculado combinando múltiplos fatores:

| Fator | Peso | Descrição |
|-------|------|-----------|
| **Menções em Documentos** | 1.0 | Quantas vezes o distrito aparece nos arquivos .txt |
| **Extrema Pobreza** | 3.0 | Quantidade e percentual de famílias em extrema pobreza |
| **Beneficiários** | 2.5 | Total de beneficiários (Bolsa Família, BPC, CadÚnico) |
| **Indicadores do Mapa** | 2.0 | Favelas, violência, mortalidade infantil, homicídios |

**Score Final** = Soma ponderada normalizada (0-100)

## 📍 Distritos Analisados

- BELA VISTA
- BOM RETIRO
- CAMBUCI
- CONSOLACAO
- LIBERDADE
- REPUBLICA
- SANTA CECILIA
- SE

## 💡 Interpretação

- **Distrito MAIOR na nuvem** = Mais necessitado = **MAIOR PRIORIDADE**
- **Distrito MENOR na nuvem** = Menos necessitado = Menor prioridade

Use a word cloud para:
- ✅ Decidir qual distrito priorizar na distribuição de cestas
- ✅ Visualizar rapidamente as áreas mais críticas
- ✅ Comunicar a situação para stakeholders

## 🔧 Estrutura do Código

```
wordcloud_distritos.py
├── processar_arquivos_txt()      # Lê e processa arquivos .txt
├── carregar_dados_extrema_pobreza()  # Carrega dados de pobreza
├── carregar_dados_beneficios()   # Carrega dados de benefícios
├── carregar_dados_mapa_desigualdade()  # Carrega indicadores do mapa
├── calcular_score_priorizacao()  # Calcula scores combinados
└── gerar_wordcloud()             # Gera a visualização
```

## 📝 Exemplo de Saída

```
📈 RESULTADO: Ranking de Priorização de Distritos

1º Lugar: SE
   Score Final: 85.32
   - Menções em documentos: 75.0
   - Extrema Pobreza: 90.5
   - Beneficiários: 88.2
   - Indicadores Mapa: 82.1

2º Lugar: BOM RETIRO
   Score Final: 78.45
   ...
```

## ⚠️ Notas Importantes

- O script é robusto e funciona mesmo se alguns dados estiverem faltando
- Se não houver menções nos documentos, usa score médio
- Dados faltantes são tratados como zero (menor prioridade)

## 🤝 Suporte

Em caso de problemas:
1. Verifique se todos os arquivos de dados existem
2. Confirme que as dependências estão instaladas
3. Verifique os logs de erro no console

