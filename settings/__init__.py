"""
Django settings for ITT data-sources project.

Generated by 'django-admin startproject' using Django 1.10.1.

For more information on this file, see
https://docs.djangoproject.com/en/1.10/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.10/ref/settings/
"""

import os
import sys
import logging

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE_ROOT = os.path.realpath(os.path.join(os.path.dirname(__file__), '..'))


# Add the local vendor libs path
sys.path.append(BASE_DIR + "/vendorlibs")


# DEFINE THE ENVIRONMENT TYPE
PRODUCTION = STAGE = DEMO = LOCAL = False
dt_key = os.environ.get('DEPLOYMENT_TYPE', 'LOCAL')
if dt_key == 'PRODUCTION':
    PRODUCTION = True
elif dt_key == 'DEMO':
    DEMO = True
elif dt_key == 'STAGE':
    STAGE = True
elif dt_key == 'LOCAL':
    LOCAL = True
else:
    raise Exception("Cannot find the DEPLOYMENT_TYPE environment variable. This is to be provided along with other vital env vars. If this instance is running locally, the '.env' file must be provided. If this instance is running on production, the environment variables have not been set up correctly. See the readme.md for more details.")


# Set up logger
if LOCAL:
    log_level = logging.DEBUG
elif PRODUCTION:
    log_level = logging.INFO
else:
    log_level = logging.DEBUG

logging.basicConfig(level=log_level)
logger = logging.getLogger(__name__)

if LOCAL or STAGE:
    logging.getLogger('boto').setLevel(logging.INFO)
    logging.getLogger('pyqs').setLevel(logging.INFO)

logger.info("Deployment environment detected: {}".format(dt_key))

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.10/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = LOCAL #or STAGE # Using settings.DEBUG leads to a memory leak in Celery

AUTH_USER_MODEL = 'user.User'

WSGI_APPLICATION = 'settings.wsgi.application'

SITE_BASE_URL = os.environ.get('SITE_BASE_URL')
SERVICE_EMAIL_ADDRESS = "info@intelligenttrading.org"
SUPPORT_EMAIL_ADDRESS = "info@intelligenttrading.org"
DEFAULT_FROM_EMAIL = "info@intelligenttrading.org"

ALLOWED_HOSTS = [
    '.intelligenttrading.org',
    '.in7el.trade',
    '.herokuapp.com',
    'localhost',
    '127.0.0.1',
]

# APPLICATION DEFINITION
INSTALLED_APPS = [
    # MAIN APPS
    'apps.common',
    'apps.user',
    'apps.channel',
    'apps.indicator',
    'apps.ai',
    'apps.signal',
    'apps.api',
    'apps.info_bot',
    'taskapp',
    'apps.backtesting',
    'apps.strategy',
    'apps.dashboard',

    # DJANGO APPS
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'django.contrib.sites',
    'django_filters',

    # PLUGINS
    'rest_framework',
    'rest_framework_swagger',

]

MIDDLEWARE = [
    'django.middleware.cache.UpdateCacheMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.cache.FetchFromCacheMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware', # for static files
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'settings.urls'

TEMPLATES = [{
    'BACKEND': 'django.template.backends.django.DjangoTemplates',
    'DIRS': [os.path.join(SITE_ROOT, 'templates'), ],
    'APP_DIRS': True,
    'OPTIONS': {
        'context_processors': [
            'django.template.context_processors.debug',
            'django.template.context_processors.request',
            'django.template.context_processors.media',
            'django.contrib.auth.context_processors.auth',
            'django.template.context_processors.static',
            'django.contrib.messages.context_processors.messages',
        ],
    },
}, ]

# Password validation
# https://docs.djangoproject.com/en/1.10/ref/settings/#auth-password-validators
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME':
        'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME':
        'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME':
        'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME':
        'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
# https://docs.djangoproject.com/en/1.10/topics/i18n/
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = False
USE_L10N = False
USE_TZ = False

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.10/howto/static-files/
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(SITE_ROOT, 'staticfiles')

# Additional locations of static files
STATICFILES_DIRS = (
    os.path.join(SITE_ROOT, 'static'),
)

STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

### START DJANGO ALLAUTH SETTINGS ###
SITE_ID = 1

LOGIN_REDIRECT_URL = '/'
ACCOUNT_EMAIL_VERIFICATION = None
ACCOUNT_ADAPTER = 'apps.user.my_adapter.MyAccountAdapter'

### END DJANGO ALLAUTH SETTINGS ###


# General apps settings

if PRODUCTION or STAGE:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

logger.info("Importing vendor_services_settings")
try:
    from settings.vendor_services_settings import *
except Exception as e:
    logger.warning("Failed to import vendor_services_settings.")
    logger.warning(str(e))


# @Alex
# Global constants
USDT_COINS = 'BTC XRP ETH ETC STR BCH LTC XMR ZEC NXT REP DASH'.split()


BTC_COINS = [
    "XRP" , "ETH" , "ETC", "STR",  "XMR",  "BCH", "LTC", "XEM", "DOGE", "ZRX", "LSK", "DASH",
    "DGB", "BTS", "SC", "ZEC", "STRAT", "BCN", "FCT", "GAME", "REP", "OMG", "VRC",
    "NXT", "STEEM", "MAID", "STORJ", "GNT", "GAS", "AMP", "SYS", "EMC2",
    "VTC", "BURST", "LBC", "GNO", "DCR", "FLO", "POT", "OMNI",
    "CVC", "PASC", "ARDR", "BCY", "GRC", "CLAM", "XCP", "VIA",
    "BTCD", "FLDC", "NAV", "NEOS", "PPC", "BLK", "EXP", "RIC",
    "NXC", "BELA", "XPM", "XVC", "XBC", "RADS", "SBD", "PINK", "NMC", "HUC", "BTM"
]

# No signals for this coins
BLACKLISTED_COINS = ['ITT', ]

# list of the exchanges on which we generate signals. Make it in sync with same list in Data app settings
#EXCHANGE_MARKETS = ('poloniex', 'binance', 'bittrex', 'bitfinex', 'kucoin')
EXCHANGE_MARKETS = ('poloniex', 'binance', 'bittrex')

# Please only add new exchanges to this settings, never remove or modify
(POLONIEX, BITTREX, BINANCE, BITFINEX, KUCOIN, GDAX, HITBTC) = list(range(7))
SOURCE_CHOICES = (
    (POLONIEX, 'poloniex'),
    (BITTREX, 'bittrex'),
    (BINANCE, 'binance'),
    (BITFINEX, 'bitfinex'),
    (KUCOIN, 'kucoin'),
    (GDAX, 'gdax'),
    (HITBTC, 'hitbtc'),
)


# list of supported counter currencies
COUNTER_CURRENCIES = ('BTC', 'ETH', 'USDT')
# Please only add new counter currencies to this settings, never remove or modify

(BTC, ETH, USDT, XMR) = list(range(4))
COUNTER_CURRENCY_CHOICES = (
    (BTC, 'BTC'),
    (ETH, 'ETH'),
    (USDT, 'USDT'),
    (XMR, 'XMR'),
)

# mapping from bin size to a name short/medium
# CHANGES TO THESE VALUES REQUIRE MAKING AND RUNNING DB MIGRATIONS
PERIODS_LIST = list([60,240,1440])
# CHANGES TO THESE VALUES REQUIRE MAKING AND RUNNING DB MIGRATIONS
(SHORT, MEDIUM, LONG) = PERIODS_LIST
HORIZONS_TIME2NAMES = {
    SHORT:'short',
    MEDIUM:'medium',
    LONG:'long'
}


A_PRIME_NUMBER = int(os.environ.get('A_PRIME_NUMBER', 12345))
TEAM_EMOJIS = os.environ.get('TEAM_EMOJIS', "🤖,").split(",")
ITT_API_KEY = os.environ.get('ITT_API_KEY', "123ABC")
REST_API_SECRET_KEY = os.environ.get('REST_API_SECRET_KEY', "123ABC")


time_speed = 1  # set to 1 for production, 10 for fast debugging
EMIT_SMA = True
EMIT_RSI = True
RUN_ANN = True
MODIFY_DB = True

EMIT_SIGNALS = os.environ.get("EMIT_SIGNALS", "true").lower() == "true" # emit if no variable set or when it set to 'true', env variables are strings

# @Alexander REST Framework settings
REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAdminUser', # Very secure by default:  only admin can access, overwrite on per-view basis
    ),
    'DEFAULT_FILTER_BACKENDS': ('django_filters.rest_framework.DjangoFilterBackend',),
}

INFO_BOT_ADMIN_USERNAME = '' # Telegram info-bot admin disabled


if LOCAL:
    logger.info("LOCAL environment detected. Importing local_settings.py")
    try:
        from settings.local_settings import *
    except:
        logger.error("Could not successfully import local_settings.py. This is necessary if you are running locally. This file should be in version control.")
        raise
