"""
Script para gerar Word Cloud de distritos priorizados por necessidade.

Este script processa arquivos .txt das pastas curated e trusted,
combina com dados de indicadores de necessidade e gera uma word cloud
onde o tamanho das palavras representa a prioridade de atendimento.

A dor da persona: com uma quantidade específica de cestas e mais famílias
do que cestas disponíveis, qual família escolher?

DEPENDÊNCIAS:
    pip install wordcloud matplotlib pandas numpy

USO:
    python wordcloud_distritos.py

SAÍDA:
    - analysis/wordcloud_distritos_priorizados.png (imagem da word cloud)
    - analysis/scores_priorizacao_distritos.csv (tabela com scores detalhados)
"""

import os
import re
import pandas as pd
import numpy as np
from pathlib import Path
from collections import Counter
from wordcloud import WordCloud
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from typing import Dict, List, Tuple, Optional

# Distritos que o projeto atende
DISTRITOS_IGREJA = [
    'BELA VISTA', 'BOM RETIRO', 'CAMBUCI', 'CONSOLACAO',
    'LIBERDADE', 'REPUBLICA', 'SANTA CECILIA', 'SE'
]

# Mapeamento de variações dos nomes dos distritos
MAPEAMENTO_DISTRITOS = {
    'BELA VISTA': ['BELA VISTA', 'BELA VISTA DISTRITO', 'BELAVISTA'],
    'BOM RETIRO': ['BOM RETIRO', 'BOM RETIRO DISTRITO', 'BOMRETIRO'],
    'CAMBUCI': ['CAMBUCI', 'CAMBUCI DISTRITO'],
    'CONSOLACAO': ['CONSOLACAO', 'CONSOLACAO DISTRITO', 'CONSOLAÇÃO'],
    'LIBERDADE': ['LIBERDADE', 'LIBERDADE DISTRITO'],
    'REPUBLICA': ['REPUBLICA', 'REPUBLICA DISTRITO', 'REPÚBLICA'],
    'SANTA CECILIA': ['SANTA CECILIA', 'SANTA CECILIA DISTRITO', 'SANTA CECÍLIA'],
    'SE': ['SE', 'SE DISTRITO', 'SÉ']
}

# Mapeamento de nomes formatados para exibição
MAPEAMENTO_FORMATADO = {
    'SE': 'Sé',
    'CAMBUCI': 'Cambuci',
    'BELA VISTA': 'Bela Vista',
    'CONSOLACAO': 'Consolação',
    'SANTA CECILIA': 'Santa Cecília',
    'LIBERDADE': 'Liberdade',
    'REPUBLICA': 'República',
    'BOM RETIRO': 'Bom Retiro'
}


def normalizar_distrito(nome: str) -> str:
    """Normaliza o nome do distrito para o formato padrão."""
    if pd.isna(nome):
        return None
    
    nome_norm = str(nome).upper().strip().replace(' DISTRITO', '')
    
    for distrito_padrao, variacoes in MAPEAMENTO_DISTRITOS.items():
        if nome_norm in variacoes:
            return distrito_padrao
    
    # Verifica se contém parte do nome
    for distrito_padrao in DISTRITOS_IGREJA:
        if distrito_padrao.replace(' ', '') in nome_norm.replace(' ', ''):
            return distrito_padrao
    
    return None


def processar_arquivos_txt(pastas: List[str]) -> Dict[str, int]:
    """
    Processa todos os arquivos .txt nas pastas especificadas
    e retorna contagem de menções aos distritos.
    """
    contador_distritos = Counter()
    
    # Base directory
    base_dir = Path(__file__).parent
    crawler_dir = base_dir / 'crawler' / 'temp'
    
    for pasta in pastas:
        pasta_path = crawler_dir / pasta
        if not pasta_path.exists():
            print(f"⚠️  Aviso: Pasta {pasta_path} não encontrada")
            continue
        
        arquivos_txt = list(pasta_path.glob('*.txt'))
        print(f"\n📂 Processando {len(arquivos_txt)} arquivos .txt em {pasta}/")
        
        for arquivo in arquivos_txt:
            try:
                with open(arquivo, 'r', encoding='utf-8', errors='ignore') as f:
                    texto = f.read()
                    texto_upper = texto.upper()
                    
                    # Conta menções de cada distrito
                    for distrito in DISTRITOS_IGREJA:
                        # Busca por variações do nome do distrito
                        variacoes = MAPEAMENTO_DISTRITOS.get(distrito, [distrito])
                        
                        # Conta ocorrências (usando regex para palavras completas)
                        for variacao in variacoes:
                            # Remove acentos para busca
                            variacao_limpa = variacao.replace('Ç', 'C').replace('É', 'E').replace('Í', 'I')
                            texto_limpo = texto_upper.replace('Ç', 'C').replace('É', 'E').replace('Í', 'I')
                            
                            # Busca palavra completa (não parte de outra palavra)
                            pattern = r'\b' + re.escape(variacao_limpa) + r'\b'
                            ocorrencias = len(re.findall(pattern, texto_limpo))
                            contador_distritos[distrito] += ocorrencias
                    
            except Exception as e:
                print(f"  ⚠️  Erro ao processar {arquivo.name}: {e}")
                continue
    
    print(f"\n✅ Processamento concluído!")
    print(f"📊 Total de menções encontradas:")
    for distrito, count in contador_distritos.most_common():
        if count > 0:
            print(f"   {distrito}: {count} menções")
    
    return dict(contador_distritos)


def carregar_dados_extrema_pobreza(base_dir: Path) -> pd.DataFrame:
    """Carrega dados de extrema pobreza por distrito."""
    caminho = base_dir / 'analysis' / 'dados_pergunta_2_extrema_pobreza.csv'
    
    if not caminho.exists():
        print(f"⚠️  Arquivo não encontrado: {caminho}")
        return pd.DataFrame(columns=['Distrito', 'Score_Extrema_Pobreza'])
    
    try:
        df = pd.read_csv(caminho, encoding='utf-8')
        
        # Filtra apenas extrema pobreza e agrega por distrito
        df_extrema = df[df['Categoria'] == 'Extrema Pobreza'].copy()
        
        if len(df_extrema) > 0:
            df_extrema = df_extrema.groupby('Distrito').agg({
                'Quantidade_Familias': 'sum',
                'Percentual': 'mean'
            }).reset_index()
            
            df_extrema['Score_Extrema_Pobreza'] = (
                df_extrema['Quantidade_Familias'] * df_extrema['Percentual'] / 100
            )
            
            return df_extrema[['Distrito', 'Score_Extrema_Pobreza']]
    except Exception as e:
        print(f"⚠️  Erro ao carregar dados de extrema pobreza: {e}")
    
    return pd.DataFrame(columns=['Distrito', 'Score_Extrema_Pobreza'])


def carregar_dados_beneficios(base_dir: Path) -> pd.DataFrame:
    """Carrega dados de benefícios (Bolsa Família, BPC, CadÚnico) por distrito."""
    caminho = base_dir / 'Arquivos_Tratados' / 'Consolidados' / 'tabelao_beneficios.csv'
    
    if not caminho.exists():
        print(f"⚠️  Arquivo não encontrado: {caminho}")
        return pd.DataFrame(columns=['Distrito', 'Total_Beneficiados'])
    
    try:
        df = pd.read_csv(caminho, encoding='utf-8-sig')
        
        # Agrupa por distrito e soma beneficiados
        df_beneficios = df.groupby('Distrito').agg({
            'Quantidade_Beneficiados': 'sum'
        }).reset_index()
        
        df_beneficios = df_beneficios.rename(columns={
            'Quantidade_Beneficiados': 'Total_Beneficiados'
        })
        
        return df_beneficios
    except Exception as e:
        print(f"⚠️  Erro ao carregar dados de benefícios: {e}")
    
    return pd.DataFrame(columns=['Distrito', 'Total_Beneficiados'])


def carregar_dados_mapa_desigualdade(base_dir: Path) -> pd.DataFrame:
    """Carrega indicadores do Mapa da Desigualdade."""
    caminho = base_dir / 'Arquivos_Tratados' / 'Consolidados' / 'tabelao_indicadores_mapa.csv'
    
    if not caminho.exists():
        print(f"⚠️  Arquivo não encontrado: {caminho}")
        return pd.DataFrame()
    
    try:
        df = pd.read_csv(caminho, encoding='utf-8-sig')
        
        # Filtra apenas os distritos da igreja
        df = df[df['Distrito'].isin(DISTRITOS_IGREJA)].copy()
        
        # Seleciona indicadores relevantes para necessidade
        indicadores_prioridade = [
            'Favelas',  # Domicílios em favelas
            'Violência contra a mulher (todas)',  # Violência
            'Mortalidade infantil',  # Saúde
            'Homicídios',  # Segurança
        ]
        
        df_filtrado = df[['Distrito'] + [col for col in indicadores_prioridade if col in df.columns]].copy()
        
        return df_filtrado
    except Exception as e:
        print(f"⚠️  Erro ao carregar dados do Mapa da Desigualdade: {e}")
    
    return pd.DataFrame()


def calcular_score_priorizacao(
    mencoes_txt: Dict[str, int],
    df_extrema_pobreza: pd.DataFrame,
    df_beneficios: pd.DataFrame,
    df_mapa: pd.DataFrame
) -> pd.DataFrame:
    """
    Calcula score de priorização baseado em múltiplos fatores.
    Quanto maior o score, maior a necessidade.
    """
    # Inicializa DataFrame com distritos
    df_scores = pd.DataFrame({'Distrito': DISTRITOS_IGREJA})
    
    # 1. Score de menções nos documentos (peso: 1.0)
    df_scores['Mencoes_TXT'] = df_scores['Distrito'].map(mencoes_txt).fillna(0)
    
    # Normaliza menções (0-100)
    if df_scores['Mencoes_TXT'].max() > 0:
        df_scores['Score_Mencoes'] = (
            (df_scores['Mencoes_TXT'] / df_scores['Mencoes_TXT'].max()) * 100
        )
    else:
        df_scores['Score_Mencoes'] = 50  # Se não houver menções, score médio
    
    # 2. Score de Extrema Pobreza (peso: 3.0)
    df_scores = df_scores.merge(df_extrema_pobreza, on='Distrito', how='left')
    df_scores['Score_Extrema_Pobreza'] = df_scores['Score_Extrema_Pobreza'].fillna(0)
    if df_scores['Score_Extrema_Pobreza'].max() > 0:
        df_scores['Score_Extrema_Pobreza_Norm'] = (
            (df_scores['Score_Extrema_Pobreza'] / df_scores['Score_Extrema_Pobreza'].max()) * 100
        )
    else:
        df_scores['Score_Extrema_Pobreza_Norm'] = 0
    
    # 3. Score de Benefícios (peso: 2.5)
    df_scores = df_scores.merge(df_beneficios, on='Distrito', how='left')
    df_scores['Total_Beneficiados'] = df_scores['Total_Beneficiados'].fillna(0)
    if df_scores['Total_Beneficiados'].max() > 0:
        df_scores['Score_Beneficios_Norm'] = (
            (df_scores['Total_Beneficiados'] / df_scores['Total_Beneficiados'].max()) * 100
        )
    else:
        df_scores['Score_Beneficios_Norm'] = 0
    
    # 4. Score do Mapa da Desigualdade (peso: 2.0)
    if not df_mapa.empty and 'Distrito' in df_mapa.columns:
        df_scores = df_scores.merge(df_mapa, on='Distrito', how='left')
        
        # Calcula score combinado dos indicadores do mapa
        score_mapa = 0
        if 'Favelas' in df_mapa.columns:
            favelas = pd.to_numeric(df_scores['Favelas'], errors='coerce').fillna(0)
            if favelas.max() > 0:
                score_mapa += (favelas / favelas.max()) * 40
        
        if 'Violência contra a mulher (todas)' in df_mapa.columns:
            violencia = pd.to_numeric(
                df_scores['Violência contra a mulher (todas)'], 
                errors='coerce'
            ).fillna(0)
            if violencia.max() > 0:
                score_mapa += (violencia / violencia.max()) * 30
        
        if 'Mortalidade infantil' in df_mapa.columns:
            mortalidade = pd.to_numeric(
                df_scores['Mortalidade infantil'], 
                errors='coerce'
            ).fillna(0)
            if mortalidade.max() > 0:
                score_mapa += (mortalidade / mortalidade.max()) * 15
        
        if 'Homicídios' in df_mapa.columns:
            homicidios = pd.to_numeric(df_scores['Homicídios'], errors='coerce').fillna(0)
            if homicidios.max() > 0:
                score_mapa += (homicidios / homicidios.max()) * 15
        
        df_scores['Score_Mapa_Norm'] = score_mapa
    else:
        df_scores['Score_Mapa_Norm'] = 0
    
    # Normaliza Score_Mapa_Norm para 0-100
    if df_scores['Score_Mapa_Norm'].max() > 0:
        df_scores['Score_Mapa_Norm'] = (
            (df_scores['Score_Mapa_Norm'] / df_scores['Score_Mapa_Norm'].max()) * 100
        )
    
    # Calcula SCORE FINAL DE PRIORIZAÇÃO com pesos
    pesos = {
        'Mencoes': 1.0,
        'Extrema_Pobreza': 3.0,
        'Beneficios': 2.5,
        'Mapa': 2.0
    }
    
    df_scores['Score_Final'] = (
        df_scores['Score_Mencoes'] * pesos['Mencoes'] +
        df_scores['Score_Extrema_Pobreza_Norm'] * pesos['Extrema_Pobreza'] +
        df_scores['Score_Beneficios_Norm'] * pesos['Beneficios'] +
        df_scores['Score_Mapa_Norm'] * pesos['Mapa']
    )
    
    # Normaliza para 0-100
    peso_total = sum(pesos.values())
    df_scores['Score_Final'] = df_scores['Score_Final'] / peso_total
    
    # Ordena por score final (maior primeiro = mais necessário)
    df_scores = df_scores.sort_values('Score_Final', ascending=False).reset_index(drop=True)
    
    return df_scores


def gerar_wordcloud(df_scores: pd.DataFrame, output_path: str):
    """
    Gera word cloud onde o tamanho representa a necessidade (score).
    Usa nomes formatados para exibição.
    """
    if df_scores.empty or 'Score_Final' not in df_scores.columns:
        raise ValueError("DataFrame de scores vazio ou sem coluna 'Score_Final'")
    
    # Cria dicionário com distrito formatado -> peso (score final)
    # Multiplica por fator para garantir tamanhos visíveis
    word_freq = {}
    
    # Garante que todos os distritos tenham peso mínimo
    score_min = df_scores['Score_Final'].min()
    score_max = df_scores['Score_Final'].max()
    
    for _, row in df_scores.iterrows():
        distrito_original = row['Distrito']
        score = row['Score_Final']
        
        # Formata o nome do distrito para exibição
        distrito_formatado = MAPEAMENTO_FORMATADO.get(distrito_original, distrito_original)
        
        # Normaliza para garantir tamanhos visíveis (mínimo 50, máximo proporcional)
        if score_max > score_min:
            peso_normalizado = 50 + ((score - score_min) / (score_max - score_min)) * 300
        else:
            peso_normalizado = 100
        
        word_freq[distrito_formatado] = max(peso_normalizado, 20)  # Garante mínimo de 20
    
    # Calcula min e max de frequência para normalização de cores
    freq_min = min(word_freq.values())
    freq_max = max(word_freq.values())
    
    # Cria função de cor personalizada: palavras maiores = cores mais escuras
    def color_func(word, font_size, position, orientation, font_path, random_state):
        """
        Retorna cor baseada no peso da palavra.
        Palavras maiores (maior peso) = cores mais escuras
        Palavras menores (menor peso) = cores mais claras
        """
        # Obtém o peso da palavra
        peso = word_freq.get(word, freq_min)
        
        # Normaliza o peso entre 0 e 1
        if freq_max > freq_min:
            intensidade = (peso - freq_min) / (freq_max - freq_min)
        else:
            intensidade = 1.0
        
        # Inverte a intensidade: maior peso = cor mais escura (menor valor RGB)
        # Usa tons de vermelho: de claro (255, 200, 200) para escuro (139, 0, 0)
        # Intensidade 0 = palavra menor = cor mais clara
        # Intensidade 1 = palavra maior = cor mais escura
        
        # Cores em RGB: vermelho escuro para palavras grandes, vermelho claro para pequenas
        r = int(255 - (255 - 139) * intensidade)  # De 255 (claro) para 139 (escuro)
        g = int(200 - (200 - 0) * intensidade)    # De 200 (claro) para 0 (escuro)
        b = int(200 - (200 - 0) * intensidade)    # De 200 (claro) para 0 (escuro)
        
        # Retorna tupla RGB (o WordCloud espera tupla ou string hexadecimal)
        return (r, g, b)
    
    # Configurações da word cloud
    try:
        wordcloud = WordCloud(
            width=1600,
            height=800,
            background_color='white',
            color_func=color_func,  # Usa função de cor personalizada
            prefer_horizontal=0.7,
            relative_scaling=0.5,
            min_font_size=20,
            max_font_size=200,
            font_path=None,  # Usa fonte padrão
            collocations=False,
        ).generate_from_frequencies(word_freq)
    except Exception as e:
        print(f"⚠️  Erro ao gerar word cloud: {e}")
        print("   Tentando com configurações alternativas...")
        # Configuração alternativa mais simples
        wordcloud = WordCloud(
            width=1600,
            height=800,
            background_color='white',
            color_func=color_func,  # Usa função de cor personalizada
            max_words=8,
        ).generate_from_frequencies(word_freq)
    
    # Cria figura
    fig, ax = plt.subplots(figsize=(20, 10))
    ax.imshow(wordcloud, interpolation='bilinear')
    ax.axis('off')
    ax.set_title(
        'Distritos Prioritários para Atendimento',
        fontsize=24,
        pad=20,
        fontweight='bold'
    )
    
    plt.tight_layout()
    
    try:
        plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
        print(f"\n✅ Word Cloud salva em: {output_path}")
    except Exception as e:
        print(f"⚠️  Erro ao salvar imagem: {e}")
        # Tenta salvar com configuração alternativa
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        print(f"   Imagem salva com resolução reduzida")
    
    plt.close()  # Fecha a figura para liberar memória
    
    return wordcloud


def main():
    """Função principal."""
    print("=" * 70)
    print("☁️  WORD CLOUD - Priorização de Distritos por Necessidade")
    print("=" * 70)
    
    base_dir = Path(__file__).parent
    
    # 1. Processa arquivos .txt
    print("\n📝 Etapa 1: Processando arquivos .txt...")
    mencoes_txt = processar_arquivos_txt(['curated', 'trusted'])
    
    # 2. Carrega dados de necessidade
    print("\n📊 Etapa 2: Carregando dados de necessidade...")
    df_extrema_pobreza = carregar_dados_extrema_pobreza(base_dir)
    df_beneficios = carregar_dados_beneficios(base_dir)
    df_mapa = carregar_dados_mapa_desigualdade(base_dir)
    
    # 3. Calcula scores de priorização
    print("\n🧮 Etapa 3: Calculando scores de priorização...")
    df_scores = calcular_score_priorizacao(
        mencoes_txt, df_extrema_pobreza, df_beneficios, df_mapa
    )
    
    # Exibe resultados
    print("\n" + "=" * 70)
    print("📈 RESULTADO: Ranking de Priorização de Distritos")
    print("=" * 70)
    print("\nLegenda:")
    print("  - Score Final: 0-100 (quanto maior, maior a necessidade)")
    print("  - Fatores considerados: Menções em documentos, Extrema Pobreza,")
    print("    Quantidade de Beneficiários, Indicadores do Mapa da Desigualdade")
    print("\n" + "-" * 70)
    
    for i, (_, row) in enumerate(df_scores.iterrows(), 1):
        distrito_formatado = MAPEAMENTO_FORMATADO.get(row['Distrito'], row['Distrito'])
        print(f"\n{i}º Lugar: {distrito_formatado}")
        print(f"   Score Final: {row['Score_Final']:.2f}")
        print(f"   - Menções em documentos: {row['Score_Mencoes']:.1f}")
        print(f"   - Extrema Pobreza: {row['Score_Extrema_Pobreza_Norm']:.1f}")
        print(f"   - Beneficiários: {row['Score_Beneficios_Norm']:.1f}")
        print(f"   - Indicadores Mapa: {row['Score_Mapa_Norm']:.1f}")
    
    # Exibe ranking resumido no console
    print("\n" + "=" * 70)
    print("📊 RANKING DE PRIORIZAÇÃO")
    print("=" * 70)
    for i, (_, row) in enumerate(df_scores.iterrows(), 1):
        distrito_formatado = MAPEAMENTO_FORMATADO.get(row['Distrito'], row['Distrito'])
        marcador = ">>>" if i == 1 else ">> " if i <= 3 else ">  "
        print(f"{marcador} {i}º {distrito_formatado}: {row['Score_Final']:.1f} pts")
    print("=" * 70)
    
    # 4. Gera word cloud
    print("\n🎨 Etapa 4: Gerando Word Cloud...")
    output_dir = base_dir / 'analysis'
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / 'wordcloud_distritos_priorizados.png'
    
    gerar_wordcloud(df_scores, str(output_path))
    
    # Salva tabela de scores
    csv_output = output_dir / 'scores_priorizacao_distritos.csv'
    df_scores.to_csv(csv_output, index=False, encoding='utf-8-sig')
    print(f"✅ Tabela de scores salva em: {csv_output}")
    
    print("\n" + "=" * 70)
    print("✅ Processo concluído!")
    print("=" * 70)
    print(f"\n💡 Interpretação:")
    print(f"   Os distritos maiores na word cloud são os mais necessitados.")
    print(f"   Use este ranking para priorizar a distribuição de cestas básicas.")


if __name__ == "__main__":
    main()

