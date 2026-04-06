from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from .models import Review, ReviewLike


@login_required
@require_POST
def like_review(request, review_id):
    try:
        review = Review.objects.get(id=review_id)
    except Review.DoesNotExist:
        return JsonResponse({'error': 'Отзыв не найден'}, status=404)

    like, created = ReviewLike.objects.get_or_create(review=review, user=request.user)

    if not created:
        like.delete()
        liked = False
    else:
        liked = True

    return JsonResponse({
        'liked': liked,
        'likes_count': review.likes_count()
    })