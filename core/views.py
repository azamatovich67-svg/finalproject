from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.decorators import login_required
from products.models import Product, Category
from cart.models import Cart, CartItem
from orders.models import Order, OrderItem
from reviews.models import Review
from django.db.models import Q

# Регистрация
def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('home')  # ← после регистрации сразу на главную
    else:
        form = UserCreationForm()
    return render(request, 'register.html', {'form': form})

# Вход
def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            login(request, form.get_user())
            return redirect('home')
    else:
        form = AuthenticationForm()
    return render(request, 'login.html', {'form': form})

# Выход
def logout_view(request):
    logout(request)
    return redirect('home')

# Личный кабинет
@login_required
def profile(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'profile.html', {'orders': orders})

# Страница товара + отзывы
def product_detail(request, slug):
    product = get_object_or_404(Product, slug=slug)
    reviews = product.reviews.all().order_by('-created_at')
    if request.method == 'POST' and request.user.is_authenticated:
        text = request.POST.get('text')
        stars = int(request.POST.get('stars', 5))
        Review.objects.create(product=product, user=request.user, text=text, stars=stars)
        return redirect('product_detail', slug=slug)
    return render(request, 'product_detail.html', {'product': product, 'reviews': reviews})

# Корзина
@login_required
def cart_view(request):
    cart, _ = Cart.objects.get_or_create(user=request.user)
    items = cart.items.select_related('product')
    total = sum(i.total_price() for i in items)
    return render(request, 'cart.html', {'items': items, 'total': total})

# Добавить в корзину
@login_required
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    cart, _ = Cart.objects.get_or_create(user=request.user)
    item, created = CartItem.objects.get_or_create(cart=cart, product=product)
    if not created:
        item.quantity += 1
        item.save()
    return redirect('cart')

# Удалить из корзины
@login_required
def remove_from_cart(request, item_id):
    CartItem.objects.filter(id=item_id, cart__user=request.user).delete()
    return redirect('cart')

# Оформить заказ
@login_required
def checkout(request):
    cart, _ = Cart.objects.get_or_create(user=request.user)
    items = cart.items.select_related('product')
    total = sum(i.total_price() for i in items)
    if request.method == 'POST':
        address = request.POST.get('address')
        order = Order.objects.create(user=request.user, address=address, total=total)
        for item in items:
            OrderItem.objects.create(
                order=order, product=item.product,
                quantity=item.quantity, price=item.product.final_price()
            )
        cart.items.all().delete()
        return redirect('profile')
    return render(request, 'checkout.html', {'items': items, 'total': total})

# Поиск
def search(request):
    q = request.GET.get('q', '')
    products = Product.objects.filter(Q(name__icontains=q) | Q(brand__name__icontains=q)) if q else []
    return render(request, 'search.html', {'products': products, 'q': q})