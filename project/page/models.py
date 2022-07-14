from django.db import models
import psycopg2

# class Orders(models.Model):

# 	ID = models.IntegerField(blank=False, null=False)
# 	ORDER_NUMBER = models.IntegerField(blank=False, null=False)
# 	PRICE_USD = models.IntegerField(blank=False, null=False)
# 	SUPPLY_DATE = models.DateField(auto_now=False, auto_now_add=False, blank=False, null=False)
# 	PRICE_RUB = models.DecimalField(max_digits=18, decimal_places=2, blank=False, null=False)

# 	class Meta():
# 		ordering = ['ID']

def get_orders():

	conn = psycopg2.connect(
	host="localhost",
	database="test1",
	user="test1admin",
	password="test"
	)

	cur = conn.cursor()
	cur.execute("SELECT * FROM orders ORDER BY ID;")
	orders = cur.fetchall()

	return orders

def get_total(orders):

	total = int()
	for order in orders:
		total += order[2]

	return total

