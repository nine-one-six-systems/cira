"""API Blueprint and route registration."""

from flask import Blueprint

api_bp = Blueprint('api', __name__)

# Import routes to register them with the blueprint
from app.api.routes import health  # noqa: F401, E402
from app.api.routes import companies  # noqa: F401, E402
from app.api.routes import batch  # noqa: F401, E402
from app.api.routes import control  # noqa: F401, E402
from app.api.routes import progress  # noqa: F401, E402
from app.api.routes import entities  # noqa: F401, E402
from app.api.routes import tokens  # noqa: F401, E402
from app.api.routes import config  # noqa: F401, E402
from app.api.routes import versions  # noqa: F401, E402
from app.api.routes import export  # noqa: F401, E402
