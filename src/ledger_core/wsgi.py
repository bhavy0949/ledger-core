import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_ENV", "prod")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ledger_core.settings")

application = get_wsgi_application()
