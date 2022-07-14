from django.shortcuts import render


from .models import get_orders, get_total

def index(request):

	orders = get_orders()
	total = get_total(orders)
	context = {
	"orders" : orders,
	"total": total,
	}


	return render(
		request,
		'start_page.html',
		context)
