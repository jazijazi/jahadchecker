# services/captcha_service.py
import json
import uuid
from django.core.cache import cache
from django.utils import timezone
from datetime import timedelta

class CaptchaService:
    REDIS_PREFIX = "captcha"
    DEFAULT_EXPIRY = 600  # 10 minutes
    
    @staticmethod
    def generate_key() -> str:
        return str(uuid.uuid4())
    
    @staticmethod
    def _get_redis_key(captcha_key: str) -> str:
        return f"{CaptchaService.REDIS_PREFIX}:{captcha_key}"
    
    @classmethod
    def store_captcha_data(cls, key: str, response: str) -> bool:
        """Store CAPTCHA data in Redis using Django cache"""
        try:
            data = {
                'challenge': "local image challenge",
                'response': response.upper(),
                'created_at': timezone.now().isoformat(),
                'expires_at': (timezone.now() + timedelta(seconds=cls.DEFAULT_EXPIRY)).isoformat(),
                'is_used': False
            }
            
            redis_key = cls._get_redis_key(key)
            # Use Django's cache.set() with timeout parameter
            cache.set(redis_key, json.dumps(data), timeout=cls.DEFAULT_EXPIRY)
            return True
            
        except Exception as e:
            print(f"Error storing captcha: {e}")
            return False
    
    @classmethod
    def fetch_captcha_data(cls, key: str) -> dict | None:
        """Get CAPTCHA data from Redis"""
        try:
            redis_key = cls._get_redis_key(key)
            data = cache.get(redis_key)
            return json.loads(data) if data else None
        except Exception as e:
            print(f"Error getting captcha: {e}")
            return None
    
    @classmethod
    def validate_captcha(cls, key: str, user_response: str) -> tuple[bool, str]:
        """Validate CAPTCHA response"""
        try:
            data = cls.fetch_captcha_data(key)
            
            if not data:
                return False, "کپچا نامعتبر یا منقضی شده است"
            
            if data.get('is_used', False):
                return False, "این کپچا قبلاً استفاده شده است"
            
            # Validate response
            if data['response'].upper() != user_response.upper():
                return False, "پاسخ کپچا نادرست است"
            
            # Mark as used
            cls.mark_as_used(key)
            return True, "کپچا معتبر است"
            
        except Exception as e:
            print(f"Error validating captcha: {e}")
            return False, "خطا در اعتبارسنجی کپچا"
    
    @classmethod
    def mark_as_used(cls, key: str) -> bool:
        """Mark CAPTCHA as used"""
        try:
            data = cls.fetch_captcha_data(key)
            if data:
                data['is_used'] = True
                redis_key = cls._get_redis_key(key)
                
                # Get remaining TTL and preserve it
                try:
                    # For django-redis, we can access the raw client
                    from django_redis import get_redis_connection
                    redis_conn = get_redis_connection("default")
                    remaining_ttl = redis_conn.ttl(redis_key)
                    
                    if remaining_ttl > 0:
                        cache.set(redis_key, json.dumps(data), timeout=remaining_ttl)
                    else:
                        cache.set(redis_key, json.dumps(data), timeout=cls.DEFAULT_EXPIRY)
                except:
                    # Fallback if we can't get TTL
                    cache.set(redis_key, json.dumps(data), timeout=cls.DEFAULT_EXPIRY)
                
                return True
            return False
        except Exception as e:
            print(f"Error marking captcha as used: {e}")
            return False
    
    @classmethod
    def delete_captcha(cls, key: str) -> bool:
        """Delete CAPTCHA data"""
        try:
            redis_key = cls._get_redis_key(key)
            cache.delete(redis_key)
            return True
        except Exception as e:
            print(f"Error deleting captcha: {e}")
            return False