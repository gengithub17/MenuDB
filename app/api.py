"""JSON API (/api/v1) mirroring everything the browser UI can do, for use by
external scripts. Authenticated with a per-user API key (see
routes.account_api_key) instead of the oauth2-proxy session cookie, since
scripts cannot complete an interactive OIDC login.
"""
from flask import Blueprint, current_app, g, jsonify, request

from app.models import Dish, Ingredient, IngredientCategory
from app import services
from app.services import ValidationError

api_bp = Blueprint('api', __name__, url_prefix='/api/v1')


@api_bp.before_request
def require_api_key():
    raw_key = request.headers.get('X-API-Key')
    api_key = services.resolve_api_key(raw_key)
    if not api_key:
        return jsonify({'error': 'invalid or missing X-API-Key'}), 401
    g.api_user = api_key.user_email


def paginated(pagination):
    return {
        'items': [d.to_dict() for d in pagination.items],
        'page': pagination.page,
        'per_page': pagination.per_page,
        'total': pagination.total,
        'pages': pagination.pages
    }


def validate_dish_payload(data):
    name = (data.get('name') or '').strip()
    if not name or len(name) > 100:
        raise ValidationError('料理名は1〜100文字で入力してください')

    difficulty = data.get('difficulty', 1)
    if not isinstance(difficulty, int) or not (1 <= difficulty <= 5):
        raise ValidationError('工程は1〜5で選択してください')

    memo = data.get('memo')
    if memo is not None and len(memo) > current_app.config['MAX_MEMO_LENGTH']:
        raise ValidationError(f"メモは{current_app.config['MAX_MEMO_LENGTH']}文字以内で入力してください")

    genre_ids = data.get('genre_ids') or []
    if len(genre_ids) > current_app.config['MAX_GENRES_PER_DISH']:
        raise ValidationError(f"ジャンルは最大{current_app.config['MAX_GENRES_PER_DISH']}個まで選択できます")

    ingredient_ids = data.get('ingredient_ids') or []
    if len(ingredient_ids) > current_app.config['MAX_INGREDIENTS_PER_DISH']:
        raise ValidationError(f"原材料は最大{current_app.config['MAX_INGREDIENTS_PER_DISH']}個まで選択できます")

    return name, difficulty, memo, genre_ids, ingredient_ids


# =============================================================================
# Dishes
# =============================================================================

@api_bp.route('/dishes', methods=['GET'])
def list_dishes():
    """ingredient_ids / genre_ids are comma-separated id lists, e.g. ?ingredient_ids=1,2,3"""
    ingredient_ids = services.parse_comma_separated_ids(request.args.get('ingredient_ids', ''))
    genre_ids = services.parse_comma_separated_ids(request.args.get('genre_ids', ''))
    mode = request.args.get('mode', 'fuzzy')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', current_app.config['ITEMS_PER_PAGE'], type=int)

    dishes = services.build_dish_query(ingredient_ids, genre_ids, mode).paginate(
        page=page, per_page=per_page, error_out=False
    )
    return jsonify(paginated(dishes))


@api_bp.route('/dishes/<int:id>', methods=['GET'])
def get_dish(id):
    dish = Dish.query.get_or_404(id)
    return jsonify(dish.to_dict())


@api_bp.route('/dishes', methods=['POST'])
def create_dish():
    data = request.get_json(force=True, silent=True) or {}
    try:
        name, difficulty, memo, genre_ids, ingredient_ids = validate_dish_payload(data)
    except ValidationError as e:
        return jsonify({'error': e.message}), 400

    dish = services.create_dish(name, difficulty, memo, genre_ids, ingredient_ids)
    return jsonify(dish.to_dict()), 201


@api_bp.route('/dishes/<int:id>', methods=['PUT'])
def update_dish(id):
    dish = Dish.query.get_or_404(id)
    data = request.get_json(force=True, silent=True) or {}
    try:
        name, difficulty, memo, genre_ids, ingredient_ids = validate_dish_payload(data)
    except ValidationError as e:
        return jsonify({'error': e.message}), 400

    dish = services.update_dish(dish, name, difficulty, memo, genre_ids, ingredient_ids)
    return jsonify(dish.to_dict())


@api_bp.route('/dishes/<int:id>', methods=['DELETE'])
def delete_dish(id):
    dish = Dish.query.get_or_404(id)
    services.delete_dish(dish)
    return '', 204


# =============================================================================
# Ingredients
# =============================================================================

@api_bp.route('/ingredients', methods=['GET'])
def list_ingredients():
    query = Ingredient.query
    q = request.args.get('q', '').strip()
    if q:
        query = query.filter(Ingredient.name.contains(q))
    category_id = request.args.get('category_id', type=int)
    if category_id:
        query = query.filter_by(category_id=category_id)

    ingredients = query.order_by(Ingredient.category_id, Ingredient.display_order).all()
    return jsonify([i.to_dict() for i in ingredients])


@api_bp.route('/ingredients/<int:id>', methods=['GET'])
def get_ingredient(id):
    ingredient = Ingredient.query.get_or_404(id)
    data = ingredient.to_dict()
    data['usage'] = services.get_ingredient_usage(ingredient)
    return jsonify(data)


@api_bp.route('/ingredients', methods=['POST'])
def create_ingredient():
    data = request.get_json(force=True, silent=True) or {}
    name = (data.get('name') or '').strip()
    category_id = data.get('category_id')

    if not name:
        return jsonify({'error': '原材料名は必須です'}), 400
    if not category_id:
        return jsonify({'error': '分類は必須です'}), 400

    try:
        ingredient = services.create_ingredient(name, category_id)
    except ValidationError as e:
        return jsonify({'error': e.message}), 400

    return jsonify(ingredient.to_dict()), 201


@api_bp.route('/ingredients/<int:id>', methods=['DELETE'])
def delete_ingredient(id):
    ingredient = Ingredient.query.get_or_404(id)
    services.delete_ingredient(ingredient)
    return '', 204


# =============================================================================
# Master data
# =============================================================================

@api_bp.route('/genres', methods=['GET'])
def list_genres():
    genres = services.get_all_genres()
    return jsonify([{'id': g.id, 'name': g.name} for g in genres])


@api_bp.route('/categories', methods=['GET'])
def list_categories():
    categories = IngredientCategory.query.order_by(IngredientCategory.display_order).all()
    return jsonify([{'id': c.id, 'name': c.name} for c in categories])


# =============================================================================
# Bookmarks ("want to cook" list, scoped to the authenticated API user)
# =============================================================================

def bookmark_to_dict(bookmark):
    data = bookmark.dish.to_dict()
    data['bookmarked_at'] = bookmark.created_at.isoformat()
    data['expires_at'] = bookmark.expires_at.isoformat()
    return data


@api_bp.route('/bookmarks', methods=['GET'])
def list_bookmarks():
    rows = services.get_active_bookmarks(g.api_user)
    return jsonify([bookmark_to_dict(b) for b in rows])


@api_bp.route('/bookmarks', methods=['POST'])
def create_bookmark():
    data = request.get_json(force=True, silent=True) or {}
    dish_id = data.get('dish_id')
    dish = Dish.query.get_or_404(dish_id) if dish_id else None
    if dish is None:
        return jsonify({'error': 'dish_id は必須です'}), 400

    bookmark = services.add_bookmark(g.api_user, dish.id, current_app.config['BOOKMARK_EXPIRY_DAYS'])
    return jsonify(bookmark_to_dict(bookmark)), 201


@api_bp.route('/bookmarks/<int:dish_id>', methods=['DELETE'])
def delete_bookmark(dish_id):
    removed = services.remove_bookmark(g.api_user, dish_id)
    if not removed:
        return jsonify({'error': 'bookmark not found'}), 404
    return '', 204
