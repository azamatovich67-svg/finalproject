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

    # Недавно просмотренные
    viewed_ids = request.session.get('viewed', [])
    viewed_products = []
    if viewed_ids:
        viewed_dict = {p.id: p for p in Product.objects.filter(id__in=viewed_ids)}
        viewed_products = [viewed_dict[i] for i in viewed_ids if i in viewed_dict]

    return render(request, 'home.html', {
        'products': products,
        'categories': categories,
        'active_category': q_category or 'all',
        'viewed_products': viewed_products,
    })