"""Shared business logic used by both the HTML routes (routes.py) and the
JSON API (api.py), so dish/ingredient CRUD and search filtering behave
identically regardless of which interface is used.
"""
from datetime import datetime, timedelta
import hashlib
import secrets

from sqlalchemy import func

from app import db
from app.models import (
    ApiKey, Dish, DishBookmark, DishGenre, Ingredient, IngredientCategory, UserSearchSetting
)


class ValidationError(Exception):
    """Raised when input fails a business rule (not a field-format error)."""
    def __init__(self, message):
        super().__init__(message)
        self.message = message


# =============================================================================
# Shared parsing helpers
# =============================================================================

def parse_comma_separated_ids(value):
    """Parse comma-separated string into list of integers"""
    if not value:
        return []
    return [int(x) for x in value.split(',') if x.strip().isdigit()]


# =============================================================================
# Master data
# =============================================================================

def get_ingredients_by_category():
    return IngredientCategory.query.order_by(IngredientCategory.display_order).all()


def get_all_genres():
    return DishGenre.query.all()


# =============================================================================
# Dish search
# =============================================================================

def build_dish_query(ingredient_ids, genre_ids, mode):
    """Build a (still unpaginated) Dish query filtered by genres/ingredients."""
    query = Dish.query

    if genre_ids:
        query = query.filter(Dish.genres.any(DishGenre.id.in_(genre_ids)))

    if ingredient_ids:
        if mode == 'exact':
            for ing_id in ingredient_ids:
                query = query.filter(Dish.ingredients.any(Ingredient.id == ing_id))
        else:
            query = query.filter(Dish.ingredients.any(Ingredient.id.in_(ingredient_ids)))

    return query.order_by(Dish.updated_at.desc())


# =============================================================================
# Dish CRUD
# =============================================================================

def create_dish(name, difficulty, memo, genre_ids, ingredient_ids):
    dish = Dish(name=name, difficulty=difficulty, memo=memo)

    for genre_id in genre_ids:
        genre = DishGenre.query.get(genre_id)
        if genre:
            dish.genres.append(genre)

    for ingredient_id in ingredient_ids:
        ingredient = Ingredient.query.get(ingredient_id)
        if ingredient:
            dish.ingredients.append(ingredient)

    db.session.add(dish)
    db.session.commit()
    return dish


def update_dish(dish, name, difficulty, memo, genre_ids, ingredient_ids):
    dish.name = name
    dish.difficulty = difficulty
    dish.memo = memo

    dish.genres.clear()
    for genre_id in genre_ids:
        genre = DishGenre.query.get(genre_id)
        if genre:
            dish.genres.append(genre)

    dish.ingredients.clear()
    for ingredient_id in ingredient_ids:
        ingredient = Ingredient.query.get(ingredient_id)
        if ingredient:
            dish.ingredients.append(ingredient)

    db.session.commit()
    return dish


def delete_dish(dish):
    db.session.delete(dish)
    db.session.commit()


# =============================================================================
# Ingredient CRUD
# =============================================================================

def create_ingredient(name, category_id):
    existing = Ingredient.query.filter_by(name=name).first()
    if existing:
        raise ValidationError('同じ名前の原材料が既に存在します')

    max_order = db.session.query(func.max(Ingredient.display_order)).filter_by(
        category_id=category_id
    ).scalar() or 0

    ingredient = Ingredient(name=name, category_id=category_id, display_order=max_order + 1)
    db.session.add(ingredient)
    db.session.commit()
    return ingredient


def delete_ingredient(ingredient):
    # The CASCADE will handle removing the ingredient from dishes
    db.session.delete(ingredient)
    db.session.commit()


def get_ingredient_usage(ingredient):
    dish_count = ingredient.dishes.count()
    dish_names = [d.name for d in ingredient.dishes.limit(5).all()]
    return {
        'count': dish_count,
        'dishes': dish_names,
        'has_more': dish_count > 5
    }


# =============================================================================
# API keys
# =============================================================================

def _hash_key(raw_key):
    return hashlib.sha256(raw_key.encode('utf-8')).hexdigest()


def issue_api_key(user_email, expiry_hours):
    """Revoke any existing key for this user and issue a new one.

    Returns the raw key (shown to the user once; only its hash is stored).
    """
    ApiKey.query.filter_by(user_email=user_email).delete()

    raw_key = secrets.token_urlsafe(32)
    api_key = ApiKey(
        user_email=user_email,
        key_hash=_hash_key(raw_key),
        expires_at=datetime.utcnow() + timedelta(hours=expiry_hours)
    )
    db.session.add(api_key)
    db.session.commit()
    return raw_key, api_key


def get_active_api_key(user_email):
    return ApiKey.query.filter_by(user_email=user_email).first()


def resolve_api_key(raw_key):
    """Look up a non-expired ApiKey matching raw_key, or None."""
    if not raw_key:
        return None
    api_key = ApiKey.query.filter_by(key_hash=_hash_key(raw_key)).first()
    if not api_key or api_key.expires_at < datetime.utcnow():
        return None
    return api_key


# =============================================================================
# Bookmarks ("want to cook" list)
# =============================================================================

def _purge_expired(user_email):
    """Delete this user's already-expired rows. Caller is responsible for db.session.commit()."""
    DishBookmark.query.filter(
        DishBookmark.user_email == user_email,
        DishBookmark.expires_at < datetime.utcnow()
    ).delete(synchronize_session=False)


def add_bookmark(user_email, dish_id, expiry_days):
    """Create the bookmark, or refresh its expiry if it already exists."""
    _purge_expired(user_email)
    bookmark = DishBookmark.query.filter_by(user_email=user_email, dish_id=dish_id).first()
    if bookmark is None:
        bookmark = DishBookmark(user_email=user_email, dish_id=dish_id)
        db.session.add(bookmark)
    bookmark.expires_at = datetime.utcnow() + timedelta(days=expiry_days)
    db.session.commit()
    return bookmark


def remove_bookmark(user_email, dish_id):
    _purge_expired(user_email)
    bookmark = DishBookmark.query.filter_by(user_email=user_email, dish_id=dish_id).first()
    if bookmark is None:
        db.session.commit()  # persist the purge even if there was nothing to remove
        return False
    db.session.delete(bookmark)
    db.session.commit()
    return True


def toggle_bookmark(user_email, dish_id, expiry_days):
    """Used by the single-button web UI toggle. Returns True if now bookmarked."""
    if remove_bookmark(user_email, dish_id):
        return False
    add_bookmark(user_email, dish_id, expiry_days)
    return True


def get_active_bookmarks(user_email):
    """Read-only, no purge: filters out expired rows without writing."""
    if not user_email:
        return []
    return (DishBookmark.query
            .filter(DishBookmark.user_email == user_email, DishBookmark.expires_at > datetime.utcnow())
            .order_by(DishBookmark.created_at.desc())
            .all())


def get_bookmarked_dish_ids(user_email):
    """For rendering the bookmark icon state on search / detail pages."""
    return {b.dish_id for b in get_active_bookmarks(user_email)}


def get_bookmark_count(user_email):
    return len(get_active_bookmarks(user_email))


# =============================================================================
# Per-user search settings
# =============================================================================

def get_user_search_setting(user_email):
    if not user_email:
        return None
    return UserSearchSetting.query.filter_by(user_email=user_email).first()


def save_user_search_setting(user_email, search_mode, per_page):
    setting = UserSearchSetting.query.filter_by(user_email=user_email).first()
    if setting is None:
        setting = UserSearchSetting(user_email=user_email)
        db.session.add(setting)
    setting.search_mode = search_mode
    setting.per_page = per_page
    db.session.commit()
    return setting
