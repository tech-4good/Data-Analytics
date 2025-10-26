import os
import re
import unicodedata
import pandas as pd

def clean_cell(cell):
    if pd.isnull(cell):
        return 'NAO INFORMADO'
    if isinstance(cell, str):
        s = unicodedata.normalize('NFD', cell).upper()
        s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
        s = re.sub(r"[^\w\s.,%()-]", '', s)
        return re.sub(r'\s+', ' ', s).strip()
    return cell

def identificar_tipo(sheet_name: str) -> str:
    s = unicodedata.normalize('NFD', str(sheet_name)).upper()
    s_plain = re.sub(r'\s+', '', ''.join(c for c in s if unicodedata.category(c) != 'Mn'))
    if 'IDOSA' in s or 'IDOSO' in s:
        return 'IDOSA'
    if 'PCD' in s_plain or ('PESSOA' in s_plain and ('DEFICI' in s_plain or 'COMDEFICIENCIA' in s_plain)):
        return 'PCD'
    if 'BPC' in s_plain or 'TOTAL' in s_plain:
        return 'BPC'
    return s.replace(' ', '_')

def ler_excel_tentativas(path, sheet, max_skip=4):
    for skip in range(max_skip):
        try:
            df = pd.read_excel(path, sheet_name=sheet, skiprows=skip)
            if df.shape[1] >= 4 and len(df) > 0:
                cols_text = ' '.join(map(lambda c: str(c).upper(), df.columns[:4]))
                if any(k in cols_text for k in ('MACRO', 'SUB', 'DISTRITO', 'PREFEITURA', 'REGIAO')):
                    return df
        except Exception:
            continue
    return None

def processar_dataframe(df: pd.DataFrame, tipo='BPC'):
    df = df.iloc[:, :4].copy()
    if tipo in ('CADUNICO', 'BOLSA_FAMILIA'):
        df.columns = ['Macrorregiao', 'Subprefeitura', 'Distrito', 'Total_Familias']
        col_total = 'Total_Familias'
    else:
        df.columns = ['Macrorregiao', 'Subprefeitura', 'Distrito', 'Total']
        col_total = 'Total'

    df[['Macrorregiao', 'Subprefeitura']] = df[['Macrorregiao', 'Subprefeitura']].ffill()
    df = df.dropna(how='all')

    for c in df.columns:
        if df[c].dtype == 'object':
            df[c] = df[c].fillna('NAO INFORMADO').apply(clean_cell)
        else:
            df[c] = df[c].fillna(0)

    df = df[~((df['Macrorregiao'] == 'NAO INFORMADO') & (df['Subprefeitura'] == 'NAO INFORMADO') & (df['Distrito'] == 'NAO INFORMADO'))]
    df = df[~df['Distrito'].str.contains('TOTAL', na=False)]
    df = df[df['Distrito'] != 'NAO INFORMADO']

    df[col_total] = pd.to_numeric(df[col_total], errors='coerce').fillna(0).astype(int)
    return df[df[col_total] > 0], col_total


def processar_bpc(base_dir: str):
    print('\nProcessando BPC')
    inp = os.path.join(base_dir, 'Arquivos_Brutos', 'BPC_Setembro_2024.xlsx')
    out = os.path.join(base_dir, 'Arquivos_Tratados')
    if not os.path.exists(inp):
        print(f'Erro: Arquivo não encontrado: {inp}')
        return

    xls = pd.ExcelFile(inp)
    print(f"{len(xls.sheet_names)} sheets encontradas")
    processed = []

    for sheet in xls.sheet_names:
        print(f"\nProcessando sheet: '{sheet}'")
        tipo = identificar_tipo(sheet)
        print(f"Tipo: {tipo}")
        df = ler_excel_tentativas(inp, sheet)
        if df is None:
            print('Estrutura não encontrada')
            continue

        df, col_total = processar_dataframe(df, 'BPC')
        df['Tipo_Beneficio'] = tipo
        df['Mes'] = 'SETEMBRO'
        df['Ano'] = 2024

        fname = f'bpc_2024_{tipo.lower()}.csv'
        df.to_csv(os.path.join(out, fname), index=False, encoding='utf-8-sig')
        print(f'Registros: {len(df)}, Total: {df[col_total].sum():,}')
        print(f'Arquivo: {fname}')
        processed.append(df)

    if processed:
        all_df = pd.concat(processed, ignore_index=True)
        all_df.to_csv(os.path.join(out, 'bpc_2024_consolidado.csv'), index=False, encoding='utf-8-sig')
        print(f"\nConsolidado: {len(all_df)} registros, {all_df['Total'].sum():,} beneficiados")
        resumo = all_df.groupby('Tipo_Beneficio')['Total'].sum()
        print('\nResumo por tipo:')
        for tipo, total in resumo.items():
            print(f'  {tipo}: {int(total):,} beneficiados')

def processar_arquivo_generico(base_dir, arquivo, saida, mes, ano, tipo):
    print(f"\nProcessando {tipo}")
    inp = os.path.join(base_dir, 'Arquivos_Brutos', arquivo)
    out = os.path.join(base_dir, 'Arquivos_Tratados')
    if not os.path.exists(inp):
        print(f'Erro: Arquivo não encontrado: {inp}')
        return
    try:
        xls = pd.ExcelFile(inp)
        sheet = xls.sheet_names[0]
        df = ler_excel_tentativas(inp, sheet, 5)
        if df is None:
            print('Erro: Estrutura não encontrada')
            return
        df, col_total = processar_dataframe(df, tipo.upper())
        df['Mes'] = mes; df['Ano'] = ano
        df.to_csv(os.path.join(out, saida), index=False, encoding='utf-8-sig')
        print('Processado com sucesso!')
        print(f'Registros: {len(df):,}')
        print(f'Total famílias: {df[col_total].sum():,}')
    except Exception as e:
        print(f'Erro ao processar {tipo}: {e}')

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    base_dir = os.path.dirname(script_dir)
    out = os.path.join(base_dir, 'Arquivos_Tratados')
    os.makedirs(out, exist_ok=True)
    try:
        processar_bpc(base_dir)
        processar_arquivo_generico(base_dir, 'cadunico_familias_jul24.xlsx', 'cadunico_familias_jul24_tratado.csv', 'JULHO', 2024, 'CADUNICO')
        processar_arquivo_generico(base_dir, 'programa_bolsafamilia_2024_1.xlsx', 'programa_bolsafamilia_2024_1_tratado.csv', 'JANEIRO', 2024, 'BOLSA_FAMILIA')
    except Exception as e:
        print(f'Erro geral: {str(e)[:60]}')
