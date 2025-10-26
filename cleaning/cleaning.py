import os
import re
import unicodedata
import pandas as pd

def _clean_text_cell(cell: object) -> object:
	if pd.isnull(cell):
		return cell
	if isinstance(cell, str):
		# Converte para maiúsculas
		s = cell.upper()
		
		# Remove as acentuações
		s = unicodedata.normalize('NFD', s)
		s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
		
		# Remove os caracteres especiais
		s = re.sub(r"[^A-Z0-9 \.,%()\-]", '', s)
		
		# Normaliza os espaços
		s = re.sub(r'\s+', ' ', s).strip()
		return s
	return cell

def clean_csv(input_path: str, output_path: str, sep: str = ';', remove_dots: bool = True) -> None:
	# Lê o CSV como string
	df = pd.read_csv(input_path, sep=sep, dtype=str)

	# Define a função de limpeza específica
	def clean_cell(cell):
		if pd.isnull(cell):
			return cell
		if isinstance(cell, str):
			# Converte para maiúsculas
			s = cell.upper()
			
			# Remove as acentuações
			s = unicodedata.normalize('NFD', s)
			s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
			
			# Remove os caracteres especiais (mantém ou remove pontos conforme necessário)
			if remove_dots:
				s = re.sub(r"[^A-Z0-9 ,%()\-]", '', s)
			else:
				s = re.sub(r"[^A-Z0-9 \.,%()\-]", '', s)
			
			# Normaliza os espaços
			s = re.sub(r'\s+', ' ', s).strip()
			return s
		return cell

	# Aplica a função de limpeza a todo o DataFrame
	df = df.map(lambda c: clean_cell(c) if not pd.isnull(c) else c)

	# Cria o diretório de saída se não existir
	os.makedirs(os.path.dirname(output_path), exist_ok=True)
	df.to_csv(output_path, index=False, encoding='utf-8-sig')

def clean_excel_mapa_desigualdade(input_path: str, output_csv: str) -> None:
	# Constrói o caminho absoluto se necessário
	if not os.path.isabs(input_path):
		script_dir = os.path.dirname(os.path.abspath(__file__))
		base_dir = os.path.dirname(script_dir)
		input_path = os.path.join(base_dir, 'Arquivos_Brutos', input_path)

	# Verifica se o arquivo existe
	if not os.path.exists(input_path):
		print(f"Arquivo de entrada não encontrado: {input_path}")
		return

	# Lê a planilha específica do Excel
	df = pd.read_excel(input_path, sheet_name='2. Dados_distritos_2024')

	def _clean_cell_for_mapa(cell):
		# Substitui valores nulos por 'NAO INFORMADO'
		if pd.isnull(cell):
			return 'NAO INFORMADO'
		if isinstance(cell, str):
			return _clean_text_cell(cell)
		return cell

	# Processa cada coluna tratando valores nulos adequadamente
	for coluna in df.columns:
		nulos = df[coluna].isnull().sum()
		if nulos > 0:
			valores_nao_nulos = df[coluna].dropna()
			if len(valores_nao_nulos) > 0:
				# Verifica se a coluna contém texto
				tem_texto = any(isinstance(val, str) or any(c.isalpha() for c in str(val))
								for val in valores_nao_nulos.head(10))
				if tem_texto or 'distrito' in coluna.lower():
					df[coluna] = df[coluna].astype(str)
					df[coluna] = df[coluna].replace(['nan', 'None', 'NaN'], 'NAO INFORMADO')
					df[coluna] = df[coluna].fillna('NAO INFORMADO')
				else:
					# Tenta converter para numérico
					try:
						df[coluna] = pd.to_numeric(df[coluna], errors='coerce')
						if df[coluna].isnull().sum() > 0:
							df[coluna] = df[coluna].astype(str).replace('nan', 'NAO INFORMADO')
					except Exception:
						df[coluna] = df[coluna].fillna('NAO INFORMADO')

	# Aplica limpeza de texto nas colunas de tipo object
	for coluna in df.columns:
		if df[coluna].dtype == 'object':
			df[coluna] = df[coluna].apply(_clean_cell_for_mapa)

	# Salva o resultado em CSV
	os.makedirs(os.path.dirname(output_csv), exist_ok=True)
	df.to_csv(output_csv, index=False, encoding='utf-8-sig')

def identificar_tipo(sheet_name: str) -> str:
	# Normaliza o nome da planilha removendo acentos
	s = unicodedata.normalize('NFD', str(sheet_name)).upper()
	s_plain = re.sub(r'\s+', '', ''.join(c for c in s if unicodedata.category(c) != 'Mn'))
	
	# Identifica o tipo de benefício
	if 'IDOSA' in s or 'IDOSO' in s:
		return 'IDOSA'
	if 'PCD' in s_plain or ('PESSOA' in s_plain and ('DEFICI' in s_plain or 'COMDEFICIENCIA' in s_plain)):
		return 'PCD'
	if 'BPC' in s_plain or 'TOTAL' in s_plain:
		return 'BPC'
	return s.replace(' ', '_')

def ler_excel_tentativas(path: str, sheet: str, max_skip: int = 4):
	# Tenta ler o Excel pulando linhas até encontrar o cabeçalho correto
	for skip in range(max_skip):
		try:
			df = pd.read_excel(path, sheet_name=sheet, skiprows=skip)
			# Verifica se encontrou estrutura válida (mínimo 4 colunas e dados)
			if df.shape[1] >= 4 and len(df) > 0:
				cols_text = ' '.join(map(lambda c: str(c).upper(), df.columns[:4]))
				if any(k in cols_text for k in ('MACRO', 'SUB', 'DISTRITO', 'PREFEITURA', 'REGIAO')):
					return df
		except Exception:
			continue
	return None

def processar_dataframe(df: pd.DataFrame, tipo: str = 'BPC'):
	# Seleciona apenas as 4 primeiras colunas
	df = df.iloc[:, :4].copy()
	
	# Define os nomes das colunas de acordo com o tipo
	if tipo in ('CADUNICO', 'BOLSA_FAMILIA'):
		df.columns = ['Macrorregiao', 'Subprefeitura', 'Distrito', 'Total_Familias']
		col_total = 'Total_Familias'
	else:
		df.columns = ['Macrorregiao', 'Subprefeitura', 'Distrito', 'Total']
		col_total = 'Total'

	# Propaga valores de Macrorregiao e Subprefeitura para baixo (forward fill)
	df[['Macrorregiao', 'Subprefeitura']] = df[['Macrorregiao', 'Subprefeitura']].ffill()
	
	# Remove linhas completamente vazias
	df = df.dropna(how='all')

	# Limpa e normaliza os dados
	for c in df.columns:
		if df[c].dtype == 'object':
			df[c] = df[c].fillna('NAO INFORMADO').apply(lambda v: _clean_text_cell(v) if not pd.isnull(v) else v)
		else:
			df[c] = df[c].fillna(0)

	# Remove linhas inválidas
	df = df[~((df['Macrorregiao'] == 'NAO INFORMADO') & (df['Subprefeitura'] == 'NAO INFORMADO') & (df['Distrito'] == 'NAO INFORMADO'))]
	df = df[~df['Distrito'].str.contains('TOTAL', na=False)]
	df = df[df['Distrito'] != 'NAO INFORMADO']

	# Converte coluna de total para inteiro
	df[col_total] = pd.to_numeric(df[col_total], errors='coerce').fillna(0).astype(int)
	
	# Retorna apenas registros com total maior que zero
	return df[df[col_total] > 0], col_total

def processar_bpc(base_dir: str):
	print('\nProcessando BPC')
	inp = os.path.join(base_dir, 'Arquivos_Brutos', 'BPC_Setembro_2024.xlsx')
	out = os.path.join(base_dir, 'Arquivos_Tratados')
	
	# Verifica se o arquivo existe
	if not os.path.exists(inp):
		print(f'Erro: Arquivo não encontrado: {inp}')
		return

	# Abre o arquivo Excel
	xls = pd.ExcelFile(inp)
	print(f"{len(xls.sheet_names)} sheets encontradas")
	processed = []

	# Processa cada planilha do arquivo
	for sheet in xls.sheet_names:
		print(f"\nProcessando sheet: '{sheet}'")
		
		# Identifica o tipo de benefício
		tipo = identificar_tipo(sheet)
		print(f"Tipo: {tipo}")
		
		# Tenta ler a planilha
		df = ler_excel_tentativas(inp, sheet)
		if df is None:
			print('Estrutura não encontrada')
			continue

		# Processa os dados da planilha
		df, col_total = processar_dataframe(df, 'BPC')
		df['Tipo_Beneficio'] = tipo
		df['Mes'] = 'SETEMBRO'
		df['Ano'] = 2024

		# Salva o arquivo processado
		fname = f'bpc_2024_{tipo.lower()}.csv'
		df.to_csv(os.path.join(out, fname), index=False, encoding='utf-8-sig')
		print(f'Registros: {len(df)}, Total: {df[col_total].sum():,}')
		print(f'Arquivo: {fname}')
		processed.append(df)

	# Cria arquivo consolidado com todos os tipos de benefício
	if processed:
		all_df = pd.concat(processed, ignore_index=True)
		all_df.to_csv(os.path.join(out, 'bpc_2024_consolidado.csv'), index=False, encoding='utf-8-sig')
		print(f"\nConsolidado: {len(all_df)} registros, {all_df['Total'].sum():,} beneficiados")
		
		# Mostra resumo por tipo de benefício
		resumo = all_df.groupby('Tipo_Beneficio')['Total'].sum()
		print('\nResumo por tipo:')
		for tipo, total in resumo.items():
			print(f'  {tipo}: {int(total):,} beneficiados')

def processar_arquivo_generico(base_dir: str, arquivo: str, saida: str, mes: str, ano: int, tipo: str):
	print(f"\nProcessando {tipo}")
	inp = os.path.join(base_dir, 'Arquivos_Brutos', arquivo)
	out = os.path.join(base_dir, 'Arquivos_Tratados')
	
	# Verifica se o arquivo existe
	if not os.path.exists(inp):
		print(f'Erro: Arquivo não encontrado: {inp}')
		return
	try:
		# Abre o arquivo Excel
		xls = pd.ExcelFile(inp)
		sheet = xls.sheet_names[0]
		
		# Tenta ler a primeira planilha
		df = ler_excel_tentativas(inp, sheet, 5)
		if df is None:
			print('Erro: Estrutura não encontrada')
			return
		
		# Processa o DataFrame
		df, col_total = processar_dataframe(df, tipo.upper())
		df['Mes'] = mes
		df['Ano'] = ano
		
		# Salva o resultado
		os.makedirs(out, exist_ok=True)
		df.to_csv(os.path.join(out, saida), index=False, encoding='utf-8-sig')
		print('Processado com sucesso!')
		print(f'Registros: {len(df):,}')
		print(f'Total famílias: {df[col_total].sum():,}')
	except Exception as e:
		print(f'Erro ao processar {tipo}: {e}')

def main():
	# Obtém o diretório base do projeto
	script_dir = os.path.dirname(os.path.abspath(__file__))
	base_dir = os.path.dirname(script_dir)
	out_dir = os.path.join(base_dir, 'Arquivos_Tratados')
	os.makedirs(out_dir, exist_ok=True)

	# Processa os arquivos CSV do ObservaSampa
	try:
		# Primeiro CSV - Indicadores
		clean_csv(
			os.path.join(base_dir, 'Arquivos_Brutos', 'ObservaSampaDadosAbertosIndicadoresCSV.csv'),
			os.path.join(out_dir, 'OSDAI_tratado.csv')
		)
		# Segundo CSV - Indicadores ODS
		clean_csv(
			os.path.join(base_dir, 'Arquivos_Brutos', 'ObservaSampaDadosAbertosIndicadoresODSCSV.csv'),
			os.path.join(out_dir, 'OSDAI_ODS_tratado.csv')
		)
		# Terceiro CSV - Variáveis
		clean_csv(
			os.path.join(base_dir, 'Arquivos_Brutos', 'ObservaSampaDadosAbertosVariaveisCSV.csv'),
			os.path.join(out_dir, 'OSDAV_tratado.csv')
		)
	except Exception as e:
		print(f'Falha ao limpar CSVs ObservaSampa: {e}')

	# Processa o Mapa da Desigualdade
	try:
		clean_excel_mapa_desigualdade('mapa_da_desigualdade_2024_dados.xlsx',
									 os.path.join(out_dir, 'mapa_da_desigualdade_2024_padronizado.csv'))
	except Exception as e:
		print(f'Falha ao processar mapa da desigualdade: {e}')

	# Processa os arquivos de benefícios
	try:
		# Processa BPC (Benefício de Prestação Continuada)
		processar_bpc(base_dir)
		
		# Processa CadÚnico
		processar_arquivo_generico(base_dir, 'cadunico_familias_jul24.xlsx', 'cadunico_familias_jul24_tratado.csv', 'JULHO', 2024, 'CADUNICO')
		
		# Processa Bolsa Família
		processar_arquivo_generico(base_dir, 'programa_bolsafamilia_2024_1.xlsx', 'programa_bolsafamilia_2024_1_tratado.csv', 'JANEIRO', 2024, 'BOLSA_FAMILIA')
	except Exception as e:
		print(f'Erro geral: {str(e)[:200]}')

if __name__ == '__main__':
	main()