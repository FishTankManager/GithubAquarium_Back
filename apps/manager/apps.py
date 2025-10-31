from django.apps import AppConfig


class ManagerConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = "apps.manager"
    label = "manager"
    verbose_name = "Manager (운영진)" # 어드민 사이드바
    
    #def ready(self):
        #from . import signals 