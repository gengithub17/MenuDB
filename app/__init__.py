import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect, CSRFError

db = SQLAlchemy()
csrf = CSRFProtect()


def create_app(config_name=None):
    """Application factory"""
    app = Flask(__name__)

    # Load configuration
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')

    from app.config import config
    app.config.from_object(config.get(config_name, config['default']))

    # Ensure data directory exists
    data_dir = os.path.dirname(app.config['DATABASE_PATH'])
    if data_dir and not os.path.exists(data_dir):
        os.makedirs(data_dir, exist_ok=True)

    # Initialize extensions
    db.init_app(app)
    csrf.init_app(app)

    # Register blueprints
    from app.routes import main_bp
    app.register_blueprint(main_bp)

    # Register error handlers
    register_error_handlers(app)

    # Create tables
    with app.app_context():
        db.create_all()
        init_master_data()

    return app


def init_master_data():
    """Initialize master data (categories and genres)"""
    from app.models import IngredientCategory, DishGenre

    # Check if data already exists
    if IngredientCategory.query.first() is not None:
        return

    # Ingredient categories
    categories = [
        {'id': 1, 'name': '肉', 'display_order': 1},
        {'id': 2, 'name': '魚介', 'display_order': 2},
        {'id': 3, 'name': '野菜', 'display_order': 3},
        {'id': 4, 'name': '加工食品', 'display_order': 4},
        {'id': 5, 'name': '既製品', 'display_order': 5},
    ]

    for cat in categories:
        db.session.add(IngredientCategory(**cat))

    # Dish genres
    genres = [
        {'id': 1, 'name': '和風'},
        {'id': 2, 'name': '洋風'},
        {'id': 3, 'name': '中華'},
        {'id': 4, 'name': 'パスタ'},
        {'id': 5, 'name': '麺'},
        {'id': 6, 'name': '海鮮'},
        {'id': 7, 'name': '汁物'},
        {'id': 8, 'name': '副菜'},
    ]

    for genre in genres:
        db.session.add(DishGenre(**genre))

    db.session.commit()


def register_error_handlers(app):
    """Register error handlers"""
    from flask import render_template

    @app.errorhandler(400)
    def bad_request(e):
        return render_template('errors/400.html'), 400

    @app.errorhandler(404)
    def not_found(e):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(e):
        db.session.rollback()
        return render_template('errors/500.html'), 500
