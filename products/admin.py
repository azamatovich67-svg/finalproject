from django.contrib import admin
from django.utils.html import format_html
from .models import Product, Category, Brand
from django.contrib.auth.models import User
from orders.models import Order

class DashboardAdmin(admin.AdminSite):
    index_title = 'Панель управления'

admin.site.index_title = 'Панель управления Voltessa'
admin.site.site_header = '⚡ Voltessa Admin'
admin.site.site_title = 'Voltessa'

class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'brand', 'category', 'colored_price', 'stock', 'created_at')
    list_filter = ('category', 'brand')
    search_fields = ('name', 'model_name')
    prepopulated_fields = {'slug': ('name',)}

    def colored_price(self, obj):
        price = obj.display_final_price()
        return format_html('<span style="color:#7c6fff; font-weight:bold;">{} сом</span>', price)
    colored_price.short_description = 'Цена'

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['total_products'] = Product.objects.count()
        extra_context['total_users'] = User.objects.count()
        extra_context['total_orders'] = Order.objects.count()
        return super().changelist_view(request, extra_context=extra_context)

class CategoryAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('name',)}

admin.site.register(Product, ProductAdmin)
admin.site.register(Category, CategoryAdmin)
admin.site.register(Brand)