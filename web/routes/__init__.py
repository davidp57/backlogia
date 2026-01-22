# routes package
# Blueprint registration

from .library import library_bp
from .api_games import api_games_bp
from .api_metadata import api_metadata_bp
from .discover import discover_bp
from .settings import settings_bp
from .sync import sync_bp
from .auth import auth_bp
from .collections import collections_bp


def register_blueprints(app):
    """Register all blueprints with the Flask app."""
    app.register_blueprint(library_bp)
    app.register_blueprint(api_games_bp)
    app.register_blueprint(api_metadata_bp)
    app.register_blueprint(discover_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(sync_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(collections_bp)
