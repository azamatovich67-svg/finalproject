from .models import Product, Category, Banner
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from core.models import Wishlist

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

    # Избранное
    wishlist_ids = []
    if request.user.is_authenticated:
        wishlist_ids = list(Wishlist.objects.filter(user=request.user).values_list('product_id', flat=True))

    # Баннеры
    banners = Banner.objects.filter(is_active=True)

    return render(request, 'home.html', {
        'products': products,
        'categories': categories,
        'active_category': q_category or 'all',
        'viewed_products': viewed_products,
        'wishlist_ids': wishlist_ids,
        'banners': banners,
    })