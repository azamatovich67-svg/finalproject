from .models import Product, Category
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required

@login_required(login_url='/register/')
def product_list(request):
    products = Product.objects.select_related('category', 'brand').all()
    categories = Category.objects.all()

    q_category = request.GET.get("category")
    if q_category:
        products = products.filter(category__slug=q_category)

    return render(request, 'home.html', {
        'products': products,
        'categories': categories,
        'active_category': q_category or 'all',
    })