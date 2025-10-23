"""
PDF Crawler Ultra Simples
Baixa PDFs de sites e salva local ou S3
"""

import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime


# ============================================================================
# CONFIGURAÇÃO - MUDE AQUI
# ============================================================================

# Onde salvar: "local" ou "s3"
MODO = "local"

# Se local, pasta de destino:
PASTA = "./downloads"

# Se S3, bucket:
BUCKET = "meu-bucket-pdfs"

# Sites para buscar PDFs:
SITES = [
    "https://olheparaafome.com.br/",
    "https://dados.prefeitura.sp.gov.br/dataset/cmbd-catalogo-municipal-de-bases-de-dados",
    "https://dados.gov.br/dados/conjuntos-dados/servicos-oferecidos-pelo-governo-do-estado-de-sao-paulo"
]

# Quantos PDFs baixar por site (None = todos):
LIMITE = 5

# Filtrar traduções/duplicatas? True/False
FILTRAR_TRADUCOES = True

# Importar configurações de filtros
try:
    from filtros import SITES_CONFIG, INDICADORES_TRADUCAO, INDICADORES_PORTUGUES
except ImportError:
    # Configuração básica se não tiver o arquivo filtros.py
    SITES_CONFIG = {}
    INDICADORES_TRADUCAO = ['english', '_en_', 'spanish', '_es_', 'french', '_fr_']
    INDICADORES_PORTUGUES = ['portuguese', 'pt_', 'brasil', '_br_']


# ============================================================================
# CÓDIGO
# ============================================================================

def filtrar_pdfs_unicos(pdfs):
    """Remove PDFs que são traduções do mesmo documento"""
    if not FILTRAR_TRADUCOES or len(pdfs) <= 1:
        return pdfs
    
    print(f"🔍 Filtrando traduções de {len(pdfs)} PDFs...")
    
    # Lista para PDFs únicos
    pdfs_unicos = []
    tamanhos_vistos = {}
    
    for pdf_url in pdfs:
        url_lower = pdf_url.lower()
        
        # 1. Verifica se contém indicadores de idioma estrangeiro
        eh_traducao = False
        for idioma in INDICADORES_TRADUCAO:
            if idioma in url_lower:
                eh_traducao = True
                print(f"  🚫 Pulando tradução por nome: {pdf_url}")
                break
        
        if eh_traducao:
            continue
        
        # 2. Verifica tamanho do arquivo para detectar duplicatas
        try:
            response = requests.head(pdf_url, timeout=10)
            tamanho = response.headers.get('content-length')
            
            if tamanho:
                tamanho = int(tamanho)
                
                # Verifica se já temos PDF com tamanho muito similar (±1KB)
                duplicata_encontrada = False
                for tam_existente in tamanhos_vistos.keys():
                    if abs(tamanho - tam_existente) <= 1024:  # Diferença ≤ 1KB
                        print(f"  🚫 Pulando duplicata por tamanho: {pdf_url}")
                        duplicata_encontrada = True
                        break
                
                if not duplicata_encontrada:
                    pdfs_unicos.append(pdf_url)
                    tamanhos_vistos[tamanho] = pdf_url
            else:
                # Se não conseguir pegar o tamanho, adiciona mesmo assim
                pdfs_unicos.append(pdf_url)
                
        except:
            # Se der erro ao verificar tamanho, adiciona mesmo assim
            pdfs_unicos.append(pdf_url)
    
    # Se filtrou tudo, pega pelo menos o primeiro
    if not pdfs_unicos and pdfs:
        print("  ⚠️  Todos foram filtrados, mantendo o primeiro PDF")
        pdfs_unicos = [pdfs[0]]
    
    print(f"  ✅ {len(pdfs_unicos)} PDFs únicos mantidos (de {len(pdfs)} originais)")
    return pdfs_unicos


def encontrar_pdfs(url):
    """Encontra links de PDF numa página"""
    print(f"🔍 Buscando em: {url}")
    
    try:
        response = requests.get(url, timeout=30)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        pdfs = []
        for link in soup.find_all('a', href=True):
            href = link['href'].lower()
            if '.pdf' in href or 'pdf' in href:
                url_completa = urljoin(url, link['href'])
                pdfs.append(url_completa)
        
        # Remove duplicatas
        pdfs = list(set(pdfs))
        
        print(f"📄 Encontrados {len(pdfs)} PDFs")
        
        # Filtrar traduções se ativado
        if FILTRAR_TRADUCOES:
            pdfs = filtrar_pdfs_unicos(pdfs)
        
        return pdfs
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        return []


def baixar_pdf(url_pdf, numero, site_nome):
    """Baixa um PDF"""
    try:
        print(f"⬇️  PDF {numero}: {url_pdf}")
        
        # Download
        response = requests.get(url_pdf, stream=True, timeout=60)
        response.raise_for_status()
        
        # Nome do arquivo
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        nome = f"{site_nome}_pdf_{numero:02d}_{timestamp}.pdf"
        
        if MODO == "local":
            # Salvar local
            os.makedirs(PASTA, exist_ok=True)
            caminho = os.path.join(PASTA, nome)
            
            with open(caminho, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            print(f"✅ Salvo: {caminho}")
            
        elif MODO == "s3":
            # Upload S3
            import boto3
            s3 = boto3.client('s3')
            
            # Reset do stream para upload
            response = requests.get(url_pdf, stream=True, timeout=60)
            
            s3.upload_fileobj(
                response.raw,
                BUCKET,
                f"pdfs/{nome}",
                ExtraArgs={'ContentType': 'application/pdf'}
            )
            
            print(f"✅ S3: s3://{BUCKET}/pdfs/{nome}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        return False


def processar_site(url):
    """Processa um site completo"""
    # Nome do site para arquivos
    site_nome = url.split('//')[1].split('/')[0].replace('.', '_')
    dominio = url.split('//')[1].split('/')[0]
    
    # Configuração específica do site
    config_site = SITES_CONFIG.get(dominio, {})
    limite_site = config_site.get('limite_pdfs', LIMITE)
    filtrar_site = config_site.get('filtrar_traducoes', FILTRAR_TRADUCOES)
    
    print(f"⚙️  Configuração para {dominio}:")
    print(f"   - Filtrar traduções: {filtrar_site}")
    print(f"   - Limite PDFs: {limite_site or 'Ilimitado'}")
    
    # Encontrar PDFs
    pdfs = encontrar_pdfs(url)
    
    if not pdfs:
        print("🚫 Nenhum PDF encontrado")
        return
    
    # Aplicar filtro específico do site
    if filtrar_site and dominio == "olheparaafome.com.br":
        # Para o olheparaafome, ser mais rigoroso
        pdfs_filtrados = []
        for pdf_url in pdfs:
            url_lower = pdf_url.lower()
            
            # Priorizar PDFs em português ou sem indicador de idioma
            tem_portugues = any(ind in url_lower for ind in INDICADORES_PORTUGUES)
            tem_traducao = any(ind in url_lower for ind in INDICADORES_TRADUCAO)
            
            if tem_portugues or (not tem_traducao):
                pdfs_filtrados.append(pdf_url)
            else:
                print(f"  🚫 Pulando tradução: {pdf_url}")
        
        pdfs = pdfs_filtrados[:1]  # Para este site, só 1 PDF
        print(f"  ✅ Mantendo apenas 1 PDF em português")
    
    # Limitar se necessário
    if limite_site:
        pdfs = pdfs[:limite_site]
        print(f"📊 Processando {len(pdfs)} PDFs (limitado)")
    
    # Baixar cada PDF
    sucessos = 0
    for i, pdf_url in enumerate(pdfs, 1):
        if baixar_pdf(pdf_url, i, site_nome):
            sucessos += 1
    
    print(f"🎯 {sucessos}/{len(pdfs)} PDFs baixados com sucesso")


def main():
    """Executa o crawler"""
    print("🚀 PDF Crawler Ultra Simples")
    print(f"📁 Modo: {MODO}")
    
    if MODO == "s3" and BUCKET == "meu-bucket-pdfs":
        print("⚠️  Configure o BUCKET antes de usar S3!")
        return
    
    if MODO == "local":
        print(f"📂 Pasta: {PASTA}")
    else:
        print(f"☁️  Bucket: {BUCKET}")
    
    print("-" * 50)
    
    # Processar cada site
    for i, site in enumerate(SITES, 1):
        print(f"\n[{i}/{len(SITES)}] {site}")
        processar_site(site)
        print("-" * 30)
    
    print("\n✅ Crawler finalizado!")


if __name__ == "__main__":
    main()