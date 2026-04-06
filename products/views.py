from .models import Product, Category, Brand, Banner
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

@login_required(login_url='/register/')
def product_list(request):
    products = Product.objects.select_related('category', 'brand').all()
    categories = Category.objects.all()
    brands = Brand.objects.all()

    q_category = request.GET.get("category")
    if q_category:
        products = products.filter(category__slug=q_category)

    # Фильтр по бренду
    q_brand = request.GET.get("brand")
    if q_brand:
        products = products.filter(brand__id=q_brand)

    # Фильтр по цене
    price_min = request.GET.get("price_min")
    price_max = request.GET.get("price_max")
    if price_min:
        try:
            products = products.filter(price__gte=float(price_min))
        except ValueError:
            pass
    if price_max:
        try:
            products = products.filter(price__lte=float(price_max))
        except ValueError:
            pass

    # Сортировка
    sort = request.GET.get("sort", "")
    if sort == "price_asc":
        products = sorted(products, key=lambda p: p.final_price())
    elif sort == "price_desc":
        products = sorted(products, key=lambda p: p.final_price(), reverse=True)
    elif sort == "popular":
        products = products.order_by('-views_count')
    elif sort == "new":
        products = products.order_by('-created_at')

    # Недавно просмотренные
    viewed_ids = request.session.get('viewed', [])
    viewed_products = []
    if viewed_ids:
        viewed_dict = {p.id: p for p in Product.objects.filter(id__in=viewed_ids)}
        viewed_products = [viewed_dict[i] for i in viewed_ids if i in viewed_dict]

    wishlist_ids = []
    if request.user.is_authenticated:
        wishlist_ids = list(Wishlist.objects.filter(user=request.user).values_list('product_id', flat=True))

    banners = Banner.objects.filter(is_active=True)

    return render(request, 'home.html', {
        'products': products,
        'categories': categories,
        'brands': brands,
        'active_category': q_category or 'all',
        'active_brand': q_brand or '',
        'price_min': price_min or '',
        'price_max': price_max or '',
        'sort': sort,
        'viewed_products': viewed_products,
        'wishlist_ids': wishlist_ids,
        'banners': banners,
    })