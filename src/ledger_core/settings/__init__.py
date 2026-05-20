import os
import dotenv

dotenv.load_dotenv()

environment = os.environ.get("DJANGO_ENV", "dev")

if environment == "prod":
    from .prod import *
else:
    from .dev import *
