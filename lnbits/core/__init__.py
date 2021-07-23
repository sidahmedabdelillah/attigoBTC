from quart import Blueprint
from lnbits.db import Database

db = Database("database")

JWT_SECRET = "secret"
JWT_ALGORITHM = "HS256"
JWT_EXP_DELTA_SECONDS = 7200

MAIL_SERVER = "MAIL_SERVER"
MAIL_PORT = "MAIL_PORT"
MAIL_ADRESS = "MAIL_ADRESS"
MAIL_PASSWORD = "MAIL_PASSWORD"
MAIL_USE_TLS = "MAIL_USE_TLS"
MAIL_USE_SSL = "MAIL_USE_SSL"

core_app: Blueprint = Blueprint(
    "core",
    __name__,
    template_folder="templates",
    static_folder="static",
    static_url_path="/core/static",
)


from .views.api import *  # noqa
from .views.auth import * # noqa
from .views.generic import *  # noqa
from .views.public_api import *  # noqa
from .tasks import register_listeners

from lnbits.tasks import record_async

core_app.record(record_async(register_listeners))
