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

def extrair_nome_alimento(caminho_arquivo: str) -> str:
	try:
		# Lê a segunda linha do arquivo que tem o nome do alimento
		df_header = pd.read_excel(caminho_arquivo, header=None, nrows=2)
		nome_alimento = str(df_header.iloc[1, 1]).strip()
		
		# Se conseguir ler o nome do arquivo retorna ele
		if nome_alimento and nome_alimento != 'nan':
			return nome_alimento
	except Exception:
		pass

	# Usa o nome do arquivo com mapeamento
	nome_base = os.path.splitext(os.path.basename(caminho_arquivo))[0]
	mapeamento = {
		'acucar': 'Açúcar',
		'arroz': 'Arroz',
		'cafe': 'Café',
		'farinha': 'Farinha',
		'feijao': 'Feijão',
		'leite': 'Leite',
		'oleo': 'Óleo'
	}
	return mapeamento.get(nome_base.lower(), nome_base.title())

def processar_arquivo_alimento(caminho_arquivo: str):
	try:		
		# Extrai o nome do alimento
		nome_alimento = extrair_nome_alimento(caminho_arquivo)
		
		# Lê o arquivo pulando as 2 primeiras linhas
		df = pd.read_excel(caminho_arquivo, header=None, skiprows=2)
		
		# Verifica se o arquivo tem pelo menos duas colunas
		if df.shape[1] < 2:
			print(f"Arquivo com estrutura inadequada (menos de 2 colunas)")
			return None
		
		# Renomeia as colunas de acordo com a padronização
		df.columns = ['data', 'preco']
		
		# Remove as linhas com valores nulos na data ou preço
		df = df.dropna(subset=['data', 'preco'])
		
		if len(df) == 0:
			print(f"Nenhum dado válido encontrado")
			return None
		
		# Processa as coluna de data
		df['data'] = df['data'].astype(str).str.strip()
		
		# Separa o mês e ano
		df[['data_mes', 'data_ano']] = df['data'].str.split('-', expand=True)
		
		# Converte o mês e ano para inteiros
		df['data_mes'] = pd.to_numeric(df['data_mes'], errors='coerce').astype('Int64')
		df['data_ano'] = pd.to_numeric(df['data_ano'], errors='coerce').astype('Int64')

		# Converte os preços para float
		df['preco'] = pd.to_numeric(df['preco'], errors='coerce')
		
		# Remove as linhas com valores inválidos após a conversão
		df = df.dropna(subset=['data_mes', 'data_ano', 'preco'])
		
		# Adiciona uma coluna com nome do alimento
		df['nome'] = nome_alimento
		
		# Adiciona uma coluna com nome do mês por extenso
		meses = {
			1: 'JANEIRO', 2: 'FEVEREIRO', 3: 'MARÇO', 4: 'ABRIL',
			5: 'MAIO', 6: 'JUNHO', 7: 'JULHO', 8: 'AGOSTO',
			9: 'SETEMBRO', 10: 'OUTUBRO', 11: 'NOVEMBRO', 12: 'DEZEMBRO'
		}
		df['mes_nome'] = df['data_mes'].map(meses)
		
		# Seleciona e reordena as colunas finais
		df = df[['nome', 'preco', 'data_mes', 'mes_nome', 'data_ano']]
		
		# Ordena as linhas por ano e mês
		df = df.sort_values(['data_ano', 'data_mes']).reset_index(drop=True)
				
		return df
		
	except Exception as e:
		print(f"Erro ao processar {os.path.basename(caminho_arquivo)}: {e}")
		return None

def processar_valores_alimentos(base_dir: str):
	print('\nProcessando Valores de Alimentos')
	
	# Define os caminhos de entrada e saída
	input_folder = os.path.join(base_dir, 'Arquivos_Brutos', 'valores_alimentos')
	output_folder = os.path.join(base_dir, 'Arquivos_Tratados')
	
	# Verifica se a pasta de entrada existe
	if not os.path.exists(input_folder):
		print(f'Erro: Pasta não encontrada: {input_folder}')
		return
	
	# Cria a pasta de saída se não existir
	os.makedirs(output_folder, exist_ok=True)
	
	# Lista todos os arquivos .xls
	arquivos_xls = [f for f in os.listdir(input_folder) if f.endswith('.xls')]
	
	if not arquivos_xls:
		print(f'Erro: Nenhum arquivo .xls encontrado em {input_folder}')
		return
	
	print(f'Arquivos encontrados: {len(arquivos_xls)}')
	
	# Processa cada arquivo
	dataframes = []
	arquivos_sucesso = []
	arquivos_erro = []
	
	for arquivo in sorted(arquivos_xls):
		caminho_completo = os.path.join(input_folder, arquivo)
		df = processar_arquivo_alimento(caminho_completo)
		
		if df is not None and len(df) > 0:
			dataframes.append(df)
			arquivos_sucesso.append(arquivo)
		else:
			arquivos_erro.append(arquivo)

	# Consolida todos os aataframes
	if not dataframes:
		print('Erro: Nenhum dado foi processado com sucesso')
		return
	
	df_consolidado = pd.concat(dataframes, ignore_index=True)

	# Ordena as linhas por alimento, ano e mês
	df_consolidado = df_consolidado.sort_values(['nome', 'data_ano', 'data_mes']).reset_index(drop=True)
	
	# Salva o CSV consolidado
	output_csv = os.path.join(output_folder, 'valores_alimentos_consolidado.csv')
	df_consolidado.to_csv(output_csv, index=False, encoding='utf-8-sig')
	
	# Obtém o primeiro e último período cronologicamente
	primeiro_registro = df_consolidado.iloc[0]
	ultimo_registro = df_consolidado.iloc[-1]
	
	print('Processado com sucesso!')
	print(f'Registros: {len(df_consolidado):,}')
	print(f'Alimentos: {df_consolidado["nome"].nunique()}')
	print(f'Período: {int(primeiro_registro["data_mes"]):02d}/{int(primeiro_registro["data_ano"])} a {int(ultimo_registro["data_mes"]):02d}/{int(ultimo_registro["data_ano"])}')
	
	if arquivos_erro:
		print(f'\nArquivos com erro: {len(arquivos_erro)}')
		for arquivo in arquivos_erro:
			print(f'  {arquivo}')

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
		
		# Processa Valores de Alimentos
		processar_valores_alimentos(base_dir)
	except Exception as e:
		print(f'Erro geral: {str(e)[:200]}')

if __name__ == '__main__':
	main()