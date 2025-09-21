import os
from pathlib import Path
from decouple import config

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

try:
    SECRET_KEY = config('SECRET_KEY', cast=str)
except Exception:
    raise RuntimeError("SECRET_KEY environment variable is not set. Please define it in your environment or .env file.")


AUTH_USER_MODEL = 'accounts.User'


# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config('DEBUG',cast=bool,default=False)

if DEBUG:
    ALLOWED_HOSTS = ['*']
else:
    ALLOWED_HOSTS = ['*']

REDIS_HOST = config('REDIS_HOST',cast=str,default="redis")
REDIS_PORT = config('REDIS_PORT',cast=str,default="6379")

INSTALLED_APPS = [
    "corsheaders",
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.gis',

    'common',
    'captcha',

    'accounts',

    'drf_spectacular',
    'leaflet',
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME': config('POSTGRES_DB'),
        'USER': config('POSTGRES_USER'),
        'PASSWORD': config('POSTGRES_PASSWORD'),
        'HOST': config('POSTGRES_HOST'),
        'PORT': config('POSTGRES_PORT'),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'accounts.validators.CustomPasswordValidator',
        'OPTIONS': {
            'min_length': 8,
            'require_uppercase': True,
            'require_lowercase': True,
            'require_numbers': True,
            'require_special_chars': True,
        }
    },
]

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": f"redis://{REDIS_HOST}:{REDIS_PORT}/1",
        "KEY_PREFIX": "zarrin:django",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "IGNORE_EXCEPTIONS": True,
            "SOCKET_CONNECT_TIMEOUT": 5,
            "SOCKET_TIMEOUT": 5,
            # Max connections control
            "CONNECTION_POOL_KWARGS": {
                "max_connections": 300,
            },
        },
        "TIMEOUT": 300,
        "VERSION": 1,
    }
}
if not DEBUG:
    #Use Redis for Django sessions in production
    SESSION_ENGINE = "django.contrib.sessions.backends.cache"
    SESSION_CACHE_ALIAS = 'default'

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES':(
        # 'rest_framework.authentication.BasicAuthentication',
        # 'rest_framework.authentication.SessionAuthentication',
        'accounts.tokenization.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'accounts.permissions.HasDynamicPermission',  
    ),
    'DEFAULT_FILTER_BACKENDS': ['django_filters.rest_framework.DjangoFilterBackend'],
    'EXCEPTION_HANDLER': 'common.utils.custom_exception_handler',

    #throttling
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',
        'user': '10000/hour',

        'captcha': '10/minute',  
    },
    #spectacular
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

#CORS
CORS_ALLOW_CREDENTIALS = True

if DEBUG:
    # CORS_ALLOWED_ORIGINS = [
    #     'http://localhost:3000',
    # ]
    CORS_ORIGIN_ALLOW_ALL = True
else:
    CORS_ALLOWED_ORIGINS = [
        'http://localhost',
        'https://localhost',
    ]

#CSRF
if DEBUG:
    CSRF_TRUSTED_ORIGINS = [
        'http://localhost:3000',
    ]
else:
    CSRF_TRUSTED_ORIGINS = [
        'http://localhost',
        'https://localhost',
    ]



MEDIA_URL = '/mediabck/'  #specifies the URL prefix used for serving media files (user-uploaded files)
#path to the directory where Django will store media files uploaded by users.
if DEBUG:
    #Add this to .gitignore
    MEDIA_ROOT = os.path.join(BASE_DIR, "media")
else:
    #Change NGINX config for it!
    MEDIA_ROOT = config('MEDIA_ROOT' , cast=str)

STATIC_URL = '/staticbck/' #static files will be accessible under URLs starting with '/staticbck/'.
#collected static files should be stored in this directory 
if DEBUG:
    #Add this to .gitignore
    STATIC_ROOT = os.path.join(BASE_DIR, "static")
else:
    #Change NGINX config for it!
    STATIC_ROOT = config('STATIC_ROOT' , cast=str)

if DEBUG:
    LOGS_ROOT = os.path.join(BASE_DIR, "debuglogstorage")
else:
    LOGS_ROOT = config('LOGS_ROOT', cast=str)

SPECTACULAR_SETTINGS = {
    'TITLE': 'Zarrin API Doc',
    'DESCRIPTION': 'Zarrin Api Service Document',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,

    'COMPONENTS': {
        'securitySchemes': {
            'JWTAuth': {
                'type': 'http',
                'scheme': 'bearer',
                'bearerFormat': 'JWT',
            }
        }
    },
}

LANGUAGE_CODE = 'en-us'

LEAFLET_CONFIG = {
    'DEFAULT_CENTER': (33,53),
    'DEFAULT_ZOOM': 6,
}


TIME_ZONE = 'Asia/Tehran'

USE_I18N = True

USE_TZ = True

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

GEOSERVER = {
    "URL":config("GEOSERVER_URL"),
    "PASSWORD":config("GEOSERVER_ADMIN_PASSWORD"),
    "USER":config("GEOSERVER_ADMIN_USER"),
    "DEFAULT_WORKSPACE":config("GEOSERVER_DEFAULT_WORKSPACE"),
    "DEFAULT_STORE":config("GEOSERVER_DEFAULT_STORE"),
}