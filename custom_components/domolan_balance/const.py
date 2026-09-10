"""Constants for the Domolan Balance integration."""
from __future__ import annotations

from datetime import timedelta

DOMAIN = "domolan_balance"

BASE_URL = "https://domolan.ru"
CSRF_TOKEN_PATH = "/csrf-token"
LOGIN_PATH = "/api/login"
USER_DATA_PATH = "/api/user/data"

DEFAULT_SCAN_INTERVAL_MINUTES = 30
MIN_SCAN_INTERVAL_MINUTES = 5
DEFAULT_SCAN_INTERVAL = timedelta(minutes=DEFAULT_SCAN_INTERVAL_MINUTES)

CONF_SCAN_INTERVAL_MINUTES = "scan_interval_minutes"

ATTR_LOGIN = "login"
ATTR_TARIFF_ID = "tariff_id"
ATTR_BLOCKED_BY_LOW_BALANCE = "blocked_by_low_balance"
ATTR_BLOCK_TYPE = "block_type"
ATTR_CREDIT_BY_USER = "credit_by_user"

MANUFACTURER = "Домолан"
