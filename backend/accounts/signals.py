from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache
from .models import Apis, Tools, Roles

@receiver([post_save, post_delete], sender=Apis)
@receiver([post_save, post_delete], sender=Tools)
@receiver([post_save, post_delete], sender=Roles)
def clear_allowed_api_cache(sender, instance, **kwargs):
    """
    Delete all caches matching user:*:role:*:allowed_apis
    whenever Apis, Tools, or Roles change.
    """
    try:
        # Works only if you're using django-redis
        redis_client = cache.client.get_client()
        keys = redis_client.keys("*user:*:role:*:allowed_apis")
        if keys:
            redis_client.delete(*keys)
            print(f"Deleted {len(keys)} cache keys matching allowed_apis")
    except Exception as e:
        print(f"Cache clear failed: {e}")