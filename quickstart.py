import datetime
import time
import httplib2 
import apiclient.discovery
from oauth2client.service_account import ServiceAccountCredentials
from service_scripts import create_relation, write_data_to_db, get_usd_value, update_PRICE_RUB, update_records

      ### Создаем отношение в БД для хранения данных

RELATION_NAME = 'orders'

create_relation(RELATION_NAME)

      ## Данные для подклбчения к Google API

CREDENTIALS_FILE = 'tokens.json'  # Имя файла с закрытым ключом
SpreadsheetID = '1OV88E63sw48H4ZzYCaJIag0dXggpCiGYThDDzNJ8QEs' # ID Google таблицы

      ### Создаём API для доступа с сервисам Goggle. service - точка "входа"

credentials = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive'])
httpAuth = credentials.authorize(httplib2.Http())
service = apiclient.discovery.build('sheets', 'v4', http = httpAuth)

      ### Получаем значения из таблицы

table_values = service.spreadsheets().values().get(
  spreadsheetId=SpreadsheetID,
  range='A1:D100',
  majorDimension='ROWS'
  ).execute().get('values')

  ### Запрашиваем курс USD

request_date = datetime.date(year=2022, month=4, day=18)
usd_value = get_usd_value(request_date)

      ### Записываем данные в БД + добавляем значение в рублях для каждой закупки

write_data_to_db(RELATION_NAME, table_values[1:], usd_value)

      ### Входим в бесконечный цикл для отслеживания изменений в таблице

while True:

      ### Чтобы не превысить квоту добавляем дилей

  time.sleep(2)

      ### Запрашиваем обновленные данные

  table_values_new = service.spreadsheets().values().get(
    spreadsheetId=SpreadsheetID,
    range='A1:D100',
    majorDimension='ROWS'
    ).execute().get('values')

  today = datetime.date.today()

      ### Проверяем изменились ли данные, если не изменились, то запускаем цикл заново

  if table_values_new == table_values and request_date == today:
    continue
  
  elif request_date != today and table_values_new == table_values:

      ### Если устарела дата запроса, подтягиваем новый курс и обновляем данные в БД

    print('Request date changed')
    request_date = today
    usd_value = get_usd_value(request_date)
    update_PRICE_RUB(RELATION_NAME, table_values_new[1:], usd_value)
    
  else: 
  
      ### Если изменились данные в таблице, то обновляем данные в БД

    print('Source table changed')
    update_records(RELATION_NAME, table_values_new[1:], usd_value)
    table_values = table_values_new




