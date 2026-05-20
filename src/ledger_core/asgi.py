import os
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_ENV", "prod")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ledger_core.settings")

application = get_asgi_application()
