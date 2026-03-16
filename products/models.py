from django.db import models

class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)

    def __str__(self):
        return self.name

class Brand(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

class Product(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    discount_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    stock = models.PositiveIntegerField()
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE)
    image = models.ImageField(upload_to="products/")
    views_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    model_name = models.CharField(max_length=100, blank=True, verbose_name="Модель")
    power = models.CharField(max_length=50, blank=True, verbose_name="Мощность (Вт)")
    volume = models.CharField(max_length=50, blank=True, verbose_name="Объём (л)")
    warranty = models.CharField(max_length=50, blank=True, verbose_name="Гарантия")
    rating = models.FloatField(default=0.0, verbose_name="Рейтинг")

    def final_price(self):
        return self.discount_price if self.discount_price else self.price

    def fmt(self, value):
        return f"{int(value):,}".replace(",", " ")

    def display_price(self):
        return self.fmt(self.price)

    def display_discount(self):
        return self.fmt(self.discount_price)

    def display_final_price(self):
        return self.fmt(self.final_price())

    def __str__(self):
        return self.name