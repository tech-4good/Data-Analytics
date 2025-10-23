# PDF Crawler Simples

Download de PDFs de sites com armazenamento local ou S3.

## 🚀 Como Usar

1. **Instalar dependências**:
```bash
pip install -r requirements.txt
```

2. **Configurar no `crawler.py`**:
```python
# Onde salvar: "local" ou "s3"
MODO = "local"

# Se local:
PASTA = "./downloads"  

# Se S3:
BUCKET = "meu-bucket-pdfs"
```

3. **Executar**:
```bash
python crawler.py
```

## ⚙️ Configuração

### Apenas Local
```python
MODO = "local"
PASTA = "./downloads"
```

### Apenas S3
```python
MODO = "s3"
BUCKET = "meu-bucket-pdfs"
```

### Adicionar Sites
```python
SITES = [
    "https://site1.com",
    "https://site2.com",  # Adicione aqui
]
```

## 📝 Para S3

Configure AWS:
```bash
aws configure
```

Ou use variáveis de ambiente:
```bash
set AWS_ACCESS_KEY_ID=sua_key
set AWS_SECRET_ACCESS_KEY=sua_secret
```

## 📊 Resultado

- PDFs nomeados como: `site_pdf_01_20251023_1430.pdf`
- Local: Salvos na pasta configurada
- S3: Enviados para `s3://bucket/pdfs/`

É isso! Super simples. 🎯