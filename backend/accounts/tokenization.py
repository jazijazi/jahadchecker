import jwt
from datetime import datetime, timedelta, UTC
from typing import Tuple, Optional, Any

from django.conf import settings
from rest_framework import exceptions
from rest_framework.authentication import BaseAuthentication, get_authorization_header
from rest_framework.request import Request

from accounts.models import User


class JWTAuthentication(BaseAuthentication):
    """
    Custom JWT authentication for DRF.
    ! Clients should include the token in the Authorization header using the Bearer scheme.

    *Note: Authentication and authorization are two whole different things.
    If the client request does not include an authentication token in the header,
    do not immediately raise an exception. Instead, treat the user as anonymous.
    If a token is present, attempt to authenticate the user using the provided token.
    """
    
    def authenticate(self, request: Request) -> Optional[Tuple[User, str]]:
        """
        Authenticate the request and return a two-tuple of (user, token).
        """
        auth_header = get_authorization_header(request).split()
        
        if not auth_header or len(auth_header) != 2:
            # raise exceptions.AuthenticationFailed("لطفاً ابتدا وارد حساب کاربری خود شوید.")
            
            #treat as anonymous
            return None
            
        if auth_header[0].lower() != b'bearer':
            # raise exceptions.AuthenticationFailed("عدم دریافت توکن از هدر به درستی")
            
            #treat as anonymous
            return None
            
        try:
            token = auth_header[1].decode('utf-8')
            user_id = decode_access_token(token)
            user = User.objects.get(pk=user_id)
            return (user, token)
        except User.DoesNotExist:
            raise exceptions.AuthenticationFailed('کاربر یافت نشد')
        except jwt.ExpiredSignatureError:
            raise exceptions.AuthenticationFailed('توکن اکسپایر شده است')
        except (jwt.DecodeError, jwt.InvalidTokenError):
            raise exceptions.AuthenticationFailed('توکن نامعبر است')
        except Exception:
            raise exceptions.AuthenticationFailed('خطا در احراز هویت کاربر ')

    def authenticate_header(self, request: Request) -> str:
        """
        Return a string to be used as the value of the WWW-Authenticate header.
        """
        return 'Bearer'


def create_access_token(user_id: int,expires_in_seconds: int = 9000) -> str:
    """
    Create a new access token for the given user ID.
    Access tokens expire in 2.5 hours (9000 seconds).
    """
    return create_token(
        user_id=user_id,
        expires_delta=timedelta(seconds=expires_in_seconds),
        token_type='access'
    )


def create_refresh_token(user_id: int , expires_in_days: int = 7) -> str:
    """
    Create a new refresh token for the given user ID.
    Refresh tokens expire in 7 days.
    """
    return create_token(
        user_id=user_id,
        expires_delta=timedelta(days=expires_in_days),
        token_type='refresh'
    )


def create_token(user_id: int, expires_delta: timedelta, token_type: str) -> str:
    """
    Helper function to create a JWT token with standard claims.
    """
    now = datetime.now(UTC)
    
    payload = {
        'user_id': user_id,
        'exp': now + expires_delta,
        'iat': now,
        'type': token_type
    }
    
    return jwt.encode(
        payload, 
        settings.SECRET_KEY, 
        algorithm='HS256'
    )


def decode_access_token(token: str) -> int:
    """
    Decode an access token and return the user ID.
    """
    return decode_token(token, 'access')


def decode_refresh_token(token: str) -> int:
    """
    Decode a refresh token and return the user ID.
    """
    return decode_token(token, 'refresh')


def decode_token(token: str, expected_type: str) -> int:
    """
    Helper function to decode and validate a token.
    """
    try:
        payload = jwt.decode(
            token, 
            settings.SECRET_KEY, 
            algorithms=['HS256']
        )
        
        # Validate token type
        if payload.get('type') != expected_type:
            raise exceptions.AuthenticationFailed('Invalid token type')
            
        return payload['user_id']
    except jwt.ExpiredSignatureError:
        raise exceptions.AuthenticationFailed('Token has expired')
    except (jwt.DecodeError, jwt.InvalidTokenError):
        raise exceptions.AuthenticationFailed('Invalid token')
    except Exception:
        raise exceptions.AuthenticationFailed('Token validation failed')