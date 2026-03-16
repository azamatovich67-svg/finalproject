from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.forms import AuthenticationForm
from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from products.models import Product, Category
from cart.models import Cart, CartItem
from orders.models import Order, OrderItem
from reviews.models import Review
from django.db.models import Q

# Регистрация
class NicknameRegisterForm(forms.Form):
    username = forms.CharField(
        label='Имя пользователя (никнейм)',
        max_length=50,
        widget=forms.TextInput(attrs={'placeholder': 'Придумай никнейм...'})
    )

def register(request):
    error = None
    if request.method == 'POST':
        form = NicknameRegisterForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            if User.objects.filter(username=username).exists():
                error = 'Этот никнейм уже занят'
            else:
                user = User.objects.create_user(username=username, password=username)
                login(request, user)
                return redirect('home')
    else:
        form = NicknameRegisterForm()
    return render(request, 'register.html', {'form': form, 'error': error})

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

# Страница товара + отзывы + похожие товары
def product_detail(request, slug):
    product = get_object_or_404(Product, slug=slug)
    product.views_count += 1
    product.save()
    reviews = product.reviews.all().order_by('-created_at')
    similar = Product.objects.filter(category=product.category).exclude(slug=slug)[:4]

    # Недавно просмотренные
    viewed = request.session.get('viewed', [])
    if product.id not in viewed:
        viewed.insert(0, product.id)
    viewed = viewed[:6]
    request.session['viewed'] = viewed

    if request.method == 'POST' and request.user.is_authenticated:
        text = request.POST.get('text')
        stars = int(request.POST.get('stars', 5))
        Review.objects.create(product=product, user=request.user, text=text, stars=stars)
        return redirect('product_detail', slug=slug)
    return render(request, 'product_detail.html', {'product': product, 'reviews': reviews, 'similar': similar})

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
    q = request.GET.get('q', '').strip()
    category_id = request.GET.get('category', '')
    sort = request.GET.get('sort', '')

    categories = Category.objects.all()
    products = Product.objects.all()

    if q:
        products = products.filter(
            Q(name__icontains=q) |
            Q(brand__name__icontains=q) |
            Q(description__icontains=q) |
            Q(category__name__icontains=q) |
            Q(model_name__icontains=q)
        ).distinct()

    if category_id:
        products = products.filter(category_id=category_id)

    if sort == 'price_asc':
        products = sorted(products, key=lambda p: p.final_price())
    elif sort == 'price_desc':
        products = sorted(products, key=lambda p: p.final_price(), reverse=True)
    elif sort == 'popular':
        products = products.order_by('-views_count')
    elif sort == 'new':
        products = products.order_by('-created_at')

    return render(request, 'search.html', {
        'products': products,
        'q': q,
        'categories': categories,
        'selected_category': category_id,
        'sort': sort,
        'count': len(list(products)) if q or category_id else 0,
    })

# Контакты
def contacts(request):
    phones = [
        {'name': 'Менеджер Азамат', 'number': '996 227 860 000'},
        {'name': 'Менеджер Самат', 'number': '996 220 990 002'},
        {'name': 'Техподдержка',    'number': '996 772 797 279'},
    ]
    return render(request, 'contacts.html', {'phones': phones})