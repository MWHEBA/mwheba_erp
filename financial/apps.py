from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class FinancialConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'financial'
    verbose_name = _('الحسابات المالية')
