# ============================================================================
# CONFIGURAÇÃO DO FILTRO DE TRADUÇÕES
# ============================================================================

# Ativar/desativar filtro de traduções
FILTRAR_TRADUCOES = True

# Configurações específicas por site
SITES_CONFIG = {
    "olheparaafome.com.br": {
        "filtrar_traducoes": True,
        "limite_pdfs": 1,  # Para este site, pegar só 1 PDF
        "idiomas_prioritarios": ["pt", "portuguese", "portugues"]
    },
    
    "dados.prefeitura.sp.gov.br": {
        "filtrar_traducoes": False,  # Este site não tem traduções
        "limite_pdfs": 5,
        "idiomas_prioritarios": []
    },
    
    "dados.gov.br": {
        "filtrar_traducoes": False,
        "limite_pdfs": 3,
        "idiomas_prioritarios": []
    }
}

# Palavras que indicam tradução (para evitar)
INDICADORES_TRADUCAO = [
    # Inglês
    "english", "en_", "_en_", "-en-", "_eng", 
    
    # Espanhol  
    "spanish", "es_", "_es_", "-es-", "_esp", "español",
    
    # Francês
    "french", "fr_", "_fr_", "-fr-", "francais", "français",
    
    # Árabe
    "arabic", "ar_", "_ar_", "-ar-", 
    
    # Chinês
    "chinese", "zh_", "_zh_", "-zh-", "mandarin",
    
    # Outros
    "hindi", "hi_", "_hi_", 
    "german", "de_", "_de_",
    "italian", "it_", "_it_",
    "russian", "ru_", "_ru_",
    "japanese", "ja_", "_ja_"
]

# Palavras que indicam português (para priorizar)
INDICADORES_PORTUGUES = [
    "portuguese", "portugues", "português", "pt_", "_pt_", "-pt-",
    "brasil", "brazil", "br_", "_br_", "-br-"
]