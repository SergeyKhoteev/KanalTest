import datetime
import requests
import psycopg2
import xml.etree.ElementTree as ET
import telebot
from telethon.sync import TelegramClient
from telethon.tl.types import InputPeerUser, InputPeerChannel
from telethon import TelegramClient, sync, events


def get_usd_value(request_date):

	### Запрашиваем текущий курс 

	cbr_url = 'http://www.cbr.ru/scripts/XML_daily.asp'
	request_date = request_date.strftime('%d/%m/%Y')
	request = requests.get(url=cbr_url, params={'date_req': request_date})
	response = request.text

	### Парсим XML ответ и достаем из него нужное значение

	report = ET.fromstring(response)
	for valute in report:
		if valute[1].text == 'USD':
			usd_value = float(valute[4].text.replace(',', '.'))

	return usd_value


def connect_to_db_and_return_conn():
	conn = psycopg2.connect(
    host="localhost",
    database="test1",
    user="test1admin",
    password="test")
	
	return conn


def create_relation(relation_name):
	conn = connect_to_db_and_return_conn()
	cur = conn.cursor()
	cur.execute('''CREATE TABLE IF NOT EXISTS %s  
    	(ID INT NOT NULL,
    	ORDER_NUMBER INT PRIMARY KEY NOT NULL,
    	PRICE_USD INT NOT NULL,
    	SUPPLY_DATE DATE,
    	PRICE_RUB DECIMAL (18, 2));'''% relation_name)

	conn.commit()
	conn.close()


def telegram_bot_sendtext(bot_message):

   bot_token = '5586720101:AAHRXxwbImY5_C0KupMSGyqBpwriL3UPrPk'
   bot_chatID = '244550428'
   send_text = 'https://api.telegram.org/bot' + bot_token + '/sendMessage?chat_id=' + bot_chatID + '&parse_mode=Markdown&text=' + bot_message

   response = requests.get(send_text)

   return response.json()


def write_data_to_db(relation_name, list_with_data, usd_value):
	conn = connect_to_db_and_return_conn()
	cur = conn.cursor()

	for row in list_with_data:
		if len(row) == 4:
			if '' in row:
				continue

			ID = int(row[0])
			ORDER_NUMBER = int(row[1])
			PRICE_USD = int(row[2])
			SUPPLY_DATE = datetime.datetime.strptime(row[3], "%d.%m.%Y")
			PRICE_RUB = round(PRICE_USD * usd_value, 2)
			
			### Проверяем срок поставки, если он прошел, то отправяем уведомление

			if SUPPLY_DATE.date() < datetime.date.today():
				bot_message = "Order " + str(ORDER_NUMBER) + " expired"
				telegram_bot_sendtext(bot_message)

			query =  f"INSERT INTO {relation_name} (ID,ORDER_NUMBER,PRICE_USD,SUPPLY_DATE,PRICE_RUB) VALUES (%s, %s, %s, %s, %s) ON CONFLICT DO NOTHING;"
			data = (ID, ORDER_NUMBER, PRICE_USD, SUPPLY_DATE, PRICE_RUB)
			cur.execute(query, data)
			conn.commit()

	conn.close()

	### Обновление БД при изменении курса

def update_PRICE_RUB(relation_name, list_with_data, usd_value):

	conn = connect_to_db_and_return_conn()
	cur = conn.cursor()
	
	for row in list_with_data:
		if len(row) == 4:
			if '' in row:
				continue

			ORDER_NUMBER = int(row[1])
			PRICE_USD = int(row[2])
			PRICE_RUB = round(PRICE_USD * usd_value, 2)

			query = f"UPDATE {relation_name} SET PRICE_RUB=%s WHERE ORDER_NUMBER=%s;"
			data = (PRICE_RUB, ORDER_NUMBER)
			cur.execute(query, data)
			conn.commit()

	conn.close()


def update_records(relation_name, list_with_data, usd_value):

	conn = connect_to_db_and_return_conn()
	cur = conn.cursor()

	cur.execute(f"SELECT * FROM {relation_name};")
	db_records = cur.fetchall()

	### Генерируем словари, по которым будем вести проверку

	orders_in_db = {}
	for order in db_records:
		orders_in_db[order[1]] = (order[0], order[2], order[3])

	orders_in_table = {}
	for order in list_with_data:
		if len(order) == 4:
			if '' in order:
				continue
			orders_in_table[int(order[1])] = (int(order[0]), int(order[2]), datetime.datetime.strptime(order[3], "%d.%m.%Y").date())

	### Проверяем на необходимость включение какой-либо записи

	for key in orders_in_table.keys():
		if key not in orders_in_db.keys():
			if len(orders_in_table[key]) == 3:
				if '' in orders_in_table[key]:
					continue
				else:
					ID = orders_in_table[key][0]
					ORDER_NUMBER = key
					PRICE_USD = orders_in_table[key][1]
					SUPPLY_DATE = orders_in_table[key][2]
					PRICE_RUB = round(PRICE_USD * usd_value, 2)
					
					query = f"INSERT INTO {relation_name} (ID,ORDER_NUMBER,PRICE_USD,SUPPLY_DATE,PRICE_RUB) VALUES (%s, %s, %s, %s, %s);"
					data = (ID, ORDER_NUMBER, PRICE_USD, SUPPLY_DATE, PRICE_RUB)
					cur.execute(query, data)
					conn.commit()
					print(str(key) + " was added")

			orders_in_db[key] = orders_in_table[key]

	### Проверяем на необходимость исключения какой-либо записи

	keys_to_delete = ()
	for key in orders_in_db.keys():
		if key not in orders_in_table.keys():

			query = f"DELETE FROM {relation_name} WHERE ORDER_NUMBER={key};"
			cur.execute(query)
			conn.commit()

			keys_to_delete += (key,)
			print(str(key) + " was removed")

	for key in keys_to_delete:
		del orders_in_db[key]

	### Проверяем на соответсвие атрибутов, при расхождении  

	for order in orders_in_db.keys():
		if orders_in_db[order] != orders_in_table[order]:
			ID = orders_in_table[order][0]
			ORDER_NUMBER = order
			PRICE_USD = orders_in_table[order][1]
			SUPPLY_DATE = orders_in_table[order][2]
			PRICE_RUB = round(PRICE_USD * usd_value, 2)

			query = f"UPDATE {relation_name} SET ID=%s, PRICE_USD=%s, SUPPLY_DATE=%s, PRICE_RUB=%s WHERE ORDER_NUMBER=%s;"
			data = (ID, PRICE_USD, SUPPLY_DATE, PRICE_RUB, ORDER_NUMBER)
			cur.execute(query, data)
			conn.commit()

			print(str(order), " was updated")

	conn.close()
