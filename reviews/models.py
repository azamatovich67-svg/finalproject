from django.db import models
from django.contrib.auth.models import User
from products.models import Product


class Review(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    text = models.TextField(verbose_name="Отзыв")
    stars = models.IntegerField(default=5, verbose_name="Оценка (1-5)")
    created_at = models.DateTimeField(auto_now_add=True)

    # лайки через промежуточную модель
    likes = models.ManyToManyField(
        User,
        through='ReviewLike',
        related_name='liked_reviews'
    )

    def likes_count(self):
        return self.likes.count()

    def __str__(self):
        return f"{self.user} → {self.product} ({self.stars}★)"


class ReviewLike(models.Model):
    review = models.ForeignKey(Review, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('review', 'user')  # один пользователь = один лайк

    def __str__(self):
        return f"{self.user} ♥ отзыв #{self.review.id}"