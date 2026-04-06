from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.forms import AuthenticationForm
from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from products.models import Product, Category
from cart.models import Cart, CartItem
from orders.models import Order, OrderItem
from reviews.models import Review, ReviewLike
from django.db.models import Q, Count
from django.http import JsonResponse
from core.models import Wishlist

# Регистрация
import re

# --- Поиск: синонимы → slug категории (одно слово или фраза) ---
_SEARCH_SYNONYMS = {
    'телефон': 'telefony',
    'телефоны': 'telefony',
    'смартфон': 'telefony',
    'смартфоны': 'telefony',
    'айфон': 'telefony',
    'iphone': 'telefony',
    'холодильник': 'holodilniki',
    'холодильники': 'holodilniki',
    'морозильник': 'morozilniki',
    'морозильники': 'morozilniki',
    'морозилка': 'morozilniki',
    'стиральная машина': 'stiralnaya',
    'стиральная машинка': 'stiralnaya',
    'стиральная': 'stiralnaya',
    'стиралка': 'stiralnaya',
}

_SEARCH_MULTI = sorted(
    [(k, v) for k, v in _SEARCH_SYNONYMS.items() if ' ' in k],
    key=lambda x: -len(x[0]),
)
_SEARCH_SINGLE = {k: v for k, v in _SEARCH_SYNONYMS.items() if ' ' not in k}


def _search_tokens(s):
    s = (s or '').strip().lower().replace('ё', 'е')
    return [t for t in re.split(r'\s+', s) if t]


def _search_one_word_q(token):
    return (
        Q(name__icontains=token)
        | Q(brand__name__icontains=token)
        | Q(description__icontains=token)
        | Q(category__name__icontains=token)
        | Q(model_name__icontains=token)
        | Q(slug__icontains=token)
        | Q(power__icontains=token)
        | Q(volume__icontains=token)
        | Q(warranty__icontains=token)
    )


def _search_parse_category_and_tokens(q_norm):
    """Возвращает (slug_категории или None, список токенов для полнотекстового поиска)."""
    qn = q_norm.strip().lower().replace('ё', 'е')
    if not qn:
        return None, []

    if qn in _SEARCH_SYNONYMS:
        return _SEARCH_SYNONYMS[qn], []

    for phrase, slug in _SEARCH_MULTI:
        if phrase in qn:
            rest = ' '.join(qn.replace(phrase, ' ', 1).split())
            return slug, _search_tokens(rest)

    parts = _search_tokens(qn)
    if len(parts) == 1 and parts[0] in _SEARCH_SINGLE:
        return _SEARCH_SINGLE[parts[0]], []
    if len(parts) >= 2 and parts[0] in _SEARCH_SINGLE:
        return _SEARCH_SINGLE[parts[0]], parts[1:]

    return None, parts if parts else [qn]


def _search_relevance(product, q_lower, tokens):
    """Чем выше — тем релевантнее (для сортировки)."""
    qn = (q_lower or '').lower().replace('ё', 'е')
    score = 0.0
    name_l = product.name.lower().replace('ё', 'е')
    bl = product.brand.name.lower().replace('ё', 'е')
    ml = (product.model_name or '').lower().replace('ё', 'е')
    cl = product.category.name.lower().replace('ё', 'е')
    dl = (product.description or '').lower().replace('ё', 'е')
    slug_l = (product.slug or '').lower()

    if qn and qn in name_l:
        score += 100
    if qn and qn in bl:
        score += 45
    if qn and qn in ml:
        score += 40

    for t in tokens:
        if not t:
            continue
        if t in name_l:
            score += 22
        if t in bl:
            score += 16
        if t in ml:
            score += 14
        if t in slug_l:
            score += 12
        if t in cl:
            score += 8
        if t in dl:
            score += 4
        for fld in (product.power or '', product.volume or '', product.warranty or ''):
            if t in fld.lower().replace('ё', 'е'):
                score += 5

    score += min(getattr(product, 'views_count', 0) or 0, 400) * 0.015
    return score


class NicknameRegisterForm(forms.Form):
    username = forms.CharField(
        label='Имя пользователя (никнейм)',
        max_length=20,
        widget=forms.TextInput(attrs={'placeholder': 'Придумай никнейм...'})
    )

    def clean_username(self):
        username = self.cleaned_data['username']
        if len(username) < 4 or len(username) > 20:
            raise forms.ValidationError('Ник должен быть от 4 до 20 символов и содержать только буквы и цифры.')
        if not re.match(r'^[a-zA-Zа-яА-ЯёЁ0-9_]+$', username):
            raise forms.ValidationError('Ник должен быть от 4 до 20 символов и содержать только буквы и цифры.')
        return username


class ProfileNicknameForm(NicknameRegisterForm):
    """Та же валидация, другие подписи для страницы профиля."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].label = 'Никнейм'
        self.fields['username'].widget.attrs['placeholder'] = 'Ваш никнейм'


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

    if request.method == 'POST':
        form = ProfileNicknameForm(request.POST)
        if form.is_valid():
            new_name = form.cleaned_data['username']
            if new_name == request.user.username:
                messages.info(request, 'Никнейм без изменений.')
            elif User.objects.filter(username=new_name).exists():
                messages.error(request, 'Этот никнейм уже занят.')
            else:
                request.user.username = new_name
                request.user.set_password(new_name)
                request.user.save()
                messages.success(request, 'Никнейм обновлён. Входите с новым ником; пароль совпадает с ником.')
                return redirect('profile')
    else:
        form = ProfileNicknameForm(initial={'username': request.user.username})

    return render(request, 'profile.html', {'orders': orders, 'nickname_form': form})

# Страница товара + отзывы + похожие товары
def product_detail(request, slug):
    product = get_object_or_404(Product, slug=slug)
    product.views_count += 1
    product.save()
    similar = Product.objects.filter(category=product.category).exclude(slug=slug)[:4]

    # Недавно просмотренные
    viewed = request.session.get('viewed', [])
    if product.id not in viewed:
        viewed.insert(0, product.id)
    viewed = viewed[:6]
    request.session['viewed'] = viewed

    if request.method == 'POST' and request.user.is_authenticated:
        text = (request.POST.get('text') or '').strip()
        stars = int(request.POST.get('stars', 5))
        stars = max(1, min(5, stars))
        if text:
            Review.objects.create(product=product, user=request.user, text=text, stars=stars)
        return redirect('product_detail', slug=slug)

    reviews_qs = (
        product.reviews.all()
        .order_by('-created_at')
        .select_related('user')
        .annotate(like_count=Count('likes'))
    )
    reviews = list(reviews_qs)

    liked_review_ids = set()
    if request.user.is_authenticated and reviews:
        liked_review_ids = set(
            ReviewLike.objects.filter(
                user=request.user,
                review_id__in=[r.id for r in reviews],
            ).values_list('review_id', flat=True)
        )

    review_more_count = max(0, len(reviews) - 2)

    return render(
        request,
        'product_detail.html',
        {
            'product': product,
            'reviews': reviews,
            'liked_review_ids': liked_review_ids,
            'review_more_count': review_more_count,
            'similar': similar,
        },
    )

# Корзина
@login_required
def cart_view(request):
    cart, _ = Cart.objects.get_or_create(user=request.user)
    items = cart.items.select_related('product')
    total = sum(i.total_price() for i in items)
    wishlist_items = Wishlist.objects.filter(user=request.user).select_related('product')
    return render(request, 'cart.html', {'items': items, 'total': total, 'wishlist_items': wishlist_items})

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

# Поиск (релевантность, слова, синонимы категорий, расширенные поля)
def search(request):
    q = request.GET.get('q', '').strip()
    q_norm = ' '.join(q.split())
    category_id = request.GET.get('category', '')
    sort = request.GET.get('sort', '')

    categories = Category.objects.all()
    base = Product.objects.select_related('category', 'brand').all()

    products_list = None

    if q_norm:
        q_lower = q_norm.lower()
        cat_slug, tokens = _search_parse_category_and_tokens(q_norm)
        qs = base
        if cat_slug:
            qs = qs.filter(category__slug=cat_slug)

        if tokens:
            strict = qs
            for t in tokens:
                strict = strict.filter(_search_one_word_q(t))
            if strict.exists():
                qs = strict
            else:
                q_or = Q()
                for t in tokens:
                    q_or |= _search_one_word_q(t)
                qs = qs.filter(q_or).distinct()

        products_list = list(qs)
        score_tokens = _search_tokens(q_norm)
        if not score_tokens:
            score_tokens = [q_lower.replace('ё', 'е')]
        ql = q_lower.replace('ё', 'е')
        products_list.sort(
            key=lambda p: (
                -_search_relevance(p, ql, score_tokens),
                -getattr(p, 'views_count', 0) or 0,
            )
        )

    if category_id:
        if products_list is not None:
            products_list = [p for p in products_list if str(p.category_id) == str(category_id)]
        else:
            base = base.filter(category_id=category_id)

    if products_list is not None:
        products = products_list
        if sort == 'price_asc':
            products = sorted(products, key=lambda p: p.final_price())
        elif sort == 'price_desc':
            products = sorted(products, key=lambda p: p.final_price(), reverse=True)
        elif sort == 'popular':
            products = sorted(products, key=lambda p: -(getattr(p, 'views_count', 0) or 0))
        elif sort == 'new':
            products = sorted(products, key=lambda p: p.created_at, reverse=True)
    else:
        products = base
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
        'count': len(products) if q_norm or category_id else 0,
    })

# Контакты
def contacts(request):
    phones = [
        {'name': 'Менеджер Азамат', 'number': '996 227 860 000'},
        {'name': 'Менеджер Самат', 'number': '996 220 990 002'},
        {'name': 'Техподдержка',    'number': '996 772 797 279'},
    ]
    return render(request, 'contacts.html', {'phones': phones})

# О нас
def about(request):
    return render(request, 'about.html')

# Добавить/убрать из избранного
@login_required
def toggle_wishlist(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    wishlist_item, created = Wishlist.objects.get_or_create(user=request.user, product=product)
    if not created:
        wishlist_item.delete()
        return JsonResponse({'status': 'removed'})
    return JsonResponse({'status': 'added'})

# Страница избранного
@login_required
def wishlist_view(request):
    items = Wishlist.objects.filter(user=request.user).select_related('product')
    return render(request, 'wishlist.html', {'items': items})

# Лайк отзыва
@login_required
def like_review(request, review_id):
    review = get_object_or_404(Review, id=review_id)
    if request.user in review.likes.all():
        review.likes.remove(request.user)
        liked = False
    else:
        review.likes.add(request.user)
        liked = True
    return JsonResponse({'liked': liked, 'count': review.likes.count()})