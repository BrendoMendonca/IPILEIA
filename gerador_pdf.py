from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.platypus     import Table
import pandas as pd
import concurrent.futures
import re
import ssl
from datetime import date as dt
from reportlab.lib.styles import getSampleStyleSheet

ssl._create_default_https_context = ssl._create_unverified_context

# Leitura do arquivo de países e seleção das colunas necessárias(PAISES)
pais = pd.read_csv("https://balanca.economia.gov.br/balanca/bd/tabelas/PAIS.csv", encoding_errors="ignore", on_bad_lines='skip', sep = ";")


# Leitura do arquivo de produtos e seleção das colunas necessárias(PRODUTOS)
sh4 = pd.read_csv('https://balanca.economia.gov.br/balanca/bd/tabelas/NCM_SH.csv', sep=";", encoding_errors="ignore", on_bad_lines='skip')
sh4 = sh4[['CO_SH4', 'NO_SH4_ING']]
sh4.rename(columns = {'CO_SH4':'SH4'}, inplace = True)
sh4 = sh4.drop_duplicates().reset_index().drop('index', axis = 1)


# Leitura do arquivo de municípios e seleção das colunas necessárias(MUNICÍPIOS)
municipio = pd.read_csv('https://balanca.economia.gov.br/balanca/bd/tabelas/UF_MUN.csv', sep=";", encoding_errors="ignore", on_bad_lines='skip')
municipio = municipio[['CO_MUN_GEO', 'NO_MUN']]
municipio.rename(columns = {'CO_MUN_GEO':'CO_MUN'}, inplace = True)


# Criação do objeto PDF
pdf = canvas.Canvas('report.pdf', pagesize=letter)

#nome do arquivo
pdf.setTitle('relatorio')

#tamanho de fonte do título
pdf.setFontSize(20)

# Adiciona um título
pdf.setFillColor('black')
pdf.drawCentredString(299, 400, 'EXPORT OF PRODUCTS FROM PARAIBA REPORT')

pdf.drawInlineImage('IPILEIA\FIEP_LOGO.png', 145, 450, 320, 320, preserveAspectRatio=True)


# Função para filtrar os tipos de produtos(importação/exportação)
def formatar(csv, tipo):
  if tipo == "EXP":
    csv["TIPO"] = "e"
  elif tipo == "IMP":
    csv["TIPO"] = "i"

  # Filtra os dados apenas para o estado da Paraíba
  csv = csv[csv["SG_UF_MUN"] == "PB"]

  # Faz o join com as planilhas de países, municípios e produtos
  csv = pd.merge(csv, pais, on = "CO_PAIS")
  csv = pd.merge(csv, municipio, on = "CO_MUN")
  csv = pd.merge(csv, sh4, on = "SH4")

  # Cria uma nova coluna com a data a partir das colunas CO_ANO e CO_MES
  csv["date"] = pd.to_datetime(csv['CO_ANO'].astype(str) + '-' + csv["CO_MES"].astype(str))
  csv = csv[['KG_LIQUIDO', 'VL_FOB', 'NO_PAIS_ING', 'NO_MUN', 'NO_SH4_ING', "TIPO", "date"]]
  return csv

# Função para ler os arquivos CSV e formatar os dados
def rcsv(url):
  dfs.append(formatar(pd.read_csv(url, sep = ";"), re.findall(r"EXP|IMP", url)[0]))
  return

#criação de listas
dfs = list()
urls = list()

#solicita ao usuário um ano para começar a busca de dados
years = int(input("Ano: "))
# lista para ler os dados de cada ano e tipo
ei = ["EXP", "IMP"]

for i in range(years, dt.today().year + 1):
  for c in ei:
      urls.append(f"https://balanca.economia.gov.br/balanca/bd/comexstat-bd/mun/{c}_{str(i)}_MUN.csv")

with concurrent.futures.ThreadPoolExecutor() as executor:
  executor.map(rcsv, urls)

# concatena todos os dataframes resultantes em um dataframe único
df = pd.concat(dfs)

# ordena o dataframe por data e define a data como o índice
df = df.sort_values(by = ["date"]).set_index('date')

pd.set_option('display.max_colwidth', 10)

# exibe o dataframe
print(df)

#criando um arquivo csv a partir do dataframe
#df.to_excel("df.xlsx")
df.to_csv("df.csv")

#lendo o arquivo csv
dados_csv = pd.read_csv('df.csv')

table_data = [dados_csv.columns.tolist()] + dados_csv.values.tolist()#table_data é uma lista contendo as colunas e linhas da tabela

# Limitando a quantidade de caracteres exibidos em cada célula
max_chars = 20
table_data = [[str(cell)[:max_chars] + '...' if len(str(cell)) > max_chars else str(cell) for cell in row] for row in table_data]

# Definindo o estilo da tabela
estilo = getSampleStyleSheet()['BodyText']
estilo.fontSize = 10

def cabecalho(table_data):

  #pegando a primeira linha da tabela e definindo o estilo
  primeira_linha = Table(table_data[:1], style=[
      ('GRID', (0, 0), (-1,-1), 1, 'black'),
      ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
      ('FONTSIZE', (0, 0), (-1, -1), estilo.fontSize),
  ])
  #exibindo a primeira linha
  table_width, table_height = primeira_linha.wrapOn(pdf, 400, 400)
  primeira_linha.drawOn(pdf, 50, 780 - table_height)

#ajuste de alinhamento do cabeçalho
table_data[0][4] += ' ' * 15
table_data[0][5] += ' ' * 10

# Determinando o número máximo de linhas por página
linhas_por_pagina = 40

# Função para criar uma nova página com a tabela
def criar_pagina(pdf, table_data, inicio, fim):
    pdf.showPage()#adiciona uma nova página
    cabecalho(table_data) #função para adicionar a primeira linha da tabela(cabeçalho) em todas as páginas
    tabela_pagina = Table(table_data[inicio:fim], style=[
        ('GRID', (0, 0), (-1, -1), 1, 'black'),
        ('FONTSIZE', (0, 0), (-1, -1), estilo.fontSize),
    ])
    table_width, table_height = tabela_pagina.wrapOn(pdf, 400, 400)
    tabela_pagina.drawOn(pdf, 50, 750 - table_height)

# Verificando se a tabela precisa de páginas extras
if len(table_data) > linhas_por_pagina:
    inicio = 1
    fim = linhas_por_pagina
    criar_pagina(pdf, table_data, inicio, fim)

    # Verificando se há necessidade de mais páginas
    while fim < len(table_data):
        inicio = fim
        fim = min(fim + linhas_por_pagina, len(table_data))
        criar_pagina(pdf, table_data, inicio, fim)

# Salvando o arquivo PDF
pdf.save()
