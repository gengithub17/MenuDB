from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from app import db
from app.models import Dish, Ingredient, IngredientCategory
from app.forms import DishForm, IngredientForm, DeleteIngredientForm
from app import services
from app.services import ValidationError

main_bp = Blueprint('main', __name__)

parse_comma_separated_ids = services.parse_comma_separated_ids


def current_user_email():
    """Email of the logged-in user, as forwarded by oauth2-proxy via nginx.
    Absent when the app is reached directly (e.g. LAN access on port 5000
    bypassing nginx/oauth2-proxy).
    """
    return request.headers.get('X-Auth-Request-Email')


@main_bp.app_context_processor
def inject_bookmark_count():
    return {'bookmark_count': services.get_bookmark_count(current_user_email())}


# =============================================================================
# Search Pages
# =============================================================================

@main_bp.route('/')
def search():
    """Search page - shows results immediately using default settings"""
    categories = services.get_ingredients_by_category()
    genres = services.get_all_genres()

    user_setting = services.get_user_search_setting(current_user_email())
    default_mode = user_setting.search_mode if user_setting else current_app.config['DEFAULT_SEARCH_MODE']
    default_per_page = user_setting.per_page if user_setting else current_app.config['ITEMS_PER_PAGE']

    ingredient_ids = parse_comma_separated_ids(request.args.get('ingredient_ids', ''))
    genre_ids = parse_comma_separated_ids(request.args.get('genre_ids', ''))
    mode = request.args.get('mode', default_mode)
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', default_per_page, type=int)

    dishes = services.build_dish_query(ingredient_ids, genre_ids, mode).paginate(
        page=page, per_page=per_page, error_out=False
    )

    return render_template('search.html',
                           categories=categories,
                           genres=genres,
                           dishes=dishes,
                           selected_ingredient_ids=ingredient_ids,
                           selected_genre_ids=genre_ids,
                           search_mode=mode,
                           bookmarked_dish_ids=services.get_bookmarked_dish_ids(current_user_email()),
                           mode='search')


@main_bp.route('/edit')
def edit_mode():
    """Search page (edit mode)"""
    categories = services.get_ingredients_by_category()
    genres = services.get_all_genres()

    # Get all dishes with pagination
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', current_app.config['ITEMS_PER_PAGE'], type=int)
    dishes = Dish.query.order_by(Dish.updated_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    return render_template('edit_mode.html',
                           categories=categories,
                           genres=genres,
                           dishes=dishes,
                           mode='edit')


@main_bp.route('/search')
def search_dishes():
    """Search dishes and return results"""
    # Parse parameters
    ingredient_ids = parse_comma_separated_ids(request.args.get('ingredient_ids', ''))
    genre_ids = parse_comma_separated_ids(request.args.get('genre_ids', ''))
    mode = request.args.get('mode', 'fuzzy')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', current_app.config['ITEMS_PER_PAGE'], type=int)
    view_mode = request.args.get('view_mode', 'search')  # search or edit

    dishes = services.build_dish_query(ingredient_ids, genre_ids, mode).paginate(
        page=page, per_page=per_page, error_out=False
    )

    categories = services.get_ingredients_by_category()
    genres = services.get_all_genres()

    template = 'edit_mode.html' if view_mode == 'edit' else 'search.html'

    return render_template(template,
                           categories=categories,
                           genres=genres,
                           dishes=dishes,
                           selected_ingredient_ids=ingredient_ids,
                           selected_genre_ids=genre_ids,
                           search_mode=mode,
                           bookmarked_dish_ids=services.get_bookmarked_dish_ids(current_user_email()),
                           mode=view_mode)


# =============================================================================
# Search Default Settings
# =============================================================================

@main_bp.route('/settings/search-defaults', methods=['POST'])
def save_search_defaults():
    """Save the current user's default search mode / page size (AJAX)"""
    user_email = current_user_email()
    if not user_email:
        return jsonify({'success': False, 'error': 'ログイン経由でのみ保存できます'}), 403

    mode = request.form.get('mode')
    per_page = request.form.get('per_page', type=int)

    if mode not in ('fuzzy', 'exact') or not per_page:
        return jsonify({'success': False, 'error': '不正な設定値です'}), 400

    services.save_user_search_setting(user_email, mode, per_page)
    return jsonify({'success': True})


# =============================================================================
# Dish Detail / Form Pages
# =============================================================================

@main_bp.route('/dish/<int:id>')
def dish_detail(id):
    """Dish detail page (read-only)"""
    dish = Dish.query.get_or_404(id)
    referrer = request.args.get('referrer', request.referrer or url_for('main.search'))
    bookmarked = dish.id in services.get_bookmarked_dish_ids(current_user_email())
    return render_template('dish_detail.html', dish=dish, referrer=referrer, bookmarked=bookmarked)


@main_bp.route('/dish/new', methods=['GET', 'POST'])
def dish_new():
    """Create new dish"""
    form = DishForm()

    # Set choices for genres
    all_genres = services.get_all_genres()
    form.genre_ids.choices = [(g.id, g.name) for g in all_genres]

    if request.method == 'POST':
        # Parse comma-separated ingredient_ids from hidden field
        ingredient_ids = parse_comma_separated_ids(request.form.get('ingredient_ids', ''))
        form._ingredient_ids_list = ingredient_ids

        if form.validate_on_submit():
            dish = services.create_dish(
                name=form.name.data,
                difficulty=form.difficulty.data,
                memo=form.memo.data,
                genre_ids=form.genre_ids.data,
                ingredient_ids=ingredient_ids
            )

            user_email = current_user_email()
            if form.add_bookmark.data and user_email:
                services.add_bookmark(user_email, dish.id, current_app.config['BOOKMARK_EXPIRY_DAYS'])

            flash('料理を登録しました', 'success')
            return redirect(url_for('main.edit_mode'))

    categories = services.get_ingredients_by_category()

    return render_template('dish_form.html',
                           form=form,
                           dish=None,
                           categories=categories,
                           genres=all_genres,
                           is_new=True)


@main_bp.route('/dish/<int:id>/edit', methods=['GET', 'POST'])
def dish_edit(id):
    """Edit existing dish"""
    dish = Dish.query.get_or_404(id)
    form = DishForm(obj=dish)

    # Set choices for genres
    all_genres = services.get_all_genres()
    form.genre_ids.choices = [(g.id, g.name) for g in all_genres]

    if request.method == 'GET':
        # Pre-populate form with existing data
        form.genre_ids.data = [g.id for g in dish.genres]
        form.ingredient_ids.data = ','.join(str(i.id) for i in dish.ingredients)
        form.add_bookmark.data = dish.id in services.get_bookmarked_dish_ids(current_user_email())
        form.referrer.data = request.args.get('referrer', request.referrer or url_for('main.edit_mode'))
    else:
        # Parse comma-separated ingredient_ids from hidden field
        ingredient_ids = parse_comma_separated_ids(request.form.get('ingredient_ids', ''))
        form._ingredient_ids_list = ingredient_ids

        if form.validate_on_submit():
            services.update_dish(
                dish,
                name=form.name.data,
                difficulty=form.difficulty.data,
                memo=form.memo.data,
                genre_ids=form.genre_ids.data,
                ingredient_ids=ingredient_ids
            )

            user_email = current_user_email()
            if user_email:
                if form.add_bookmark.data:
                    services.add_bookmark(user_email, dish.id, current_app.config['BOOKMARK_EXPIRY_DAYS'])
                else:
                    services.remove_bookmark(user_email, dish.id)

            flash('料理を更新しました', 'success')

            # Return to referrer or detail page
            referrer = form.referrer.data
            if referrer and 'dish/' in referrer:
                return redirect(url_for('main.dish_detail', id=dish.id))
            return redirect(referrer or url_for('main.edit_mode'))

    categories = services.get_ingredients_by_category()
    genres = services.get_all_genres()

    return render_template('dish_form.html',
                           form=form,
                           dish=dish,
                           categories=categories,
                           genres=genres,
                           is_new=False)


@main_bp.route('/dish/<int:id>/delete', methods=['POST'])
def dish_delete(id):
    """Delete a dish"""
    dish = Dish.query.get_or_404(id)
    services.delete_dish(dish)

    flash('料理を削除しました', 'success')
    return redirect(url_for('main.edit_mode'))


# =============================================================================
# Ingredient Pages
# =============================================================================

@main_bp.route('/ingredient/new', methods=['GET', 'POST'])
def ingredient_new():
    """Create new ingredient"""
    form = IngredientForm()
    form.category_id.choices = [(c.id, c.name) for c in IngredientCategory.query.order_by(IngredientCategory.display_order).all()]

    if form.validate_on_submit():
        try:
            services.create_ingredient(form.name.data, form.category_id.data)
            flash('原材料を登録しました', 'success')

            # Return to referrer
            referrer = request.form.get('referrer') or request.referrer
            if referrer:
                return redirect(referrer)
            return redirect(url_for('main.ingredients'))
        except ValidationError as e:
            flash(e.message, 'error')

    categories = IngredientCategory.query.order_by(IngredientCategory.display_order).all()
    return render_template('ingredient_register.html',
                           form=form,
                           categories=categories)


@main_bp.route('/ingredients')
def ingredients():
    """Ingredient management page"""
    category_id = request.args.get('category_id', type=int)
    categories = services.get_ingredients_by_category()

    if category_id:
        # Filter by category
        filtered_categories = [c for c in categories if c.id == category_id]
    else:
        filtered_categories = categories

    delete_form = DeleteIngredientForm()

    return render_template('ingredient_manage.html',
                           categories=categories,
                           filtered_categories=filtered_categories,
                           selected_category_id=category_id,
                           delete_form=delete_form)


@main_bp.route('/ingredient/<int:id>/check-usage')
def ingredient_check_usage(id):
    """Check how many dishes use this ingredient (AJAX)"""
    ingredient = Ingredient.query.get_or_404(id)
    return jsonify(services.get_ingredient_usage(ingredient))


@main_bp.route('/ingredient/<int:id>/delete', methods=['POST'])
def ingredient_delete(id):
    """Delete an ingredient"""
    ingredient = Ingredient.query.get_or_404(id)
    services.delete_ingredient(ingredient)

    flash(f'「{ingredient.name}」を削除しました', 'success')
    return redirect(url_for('main.ingredients'))


# =============================================================================
# Bookmarks ("want to cook" list - manual or 1-week auto expiry)
# =============================================================================

@main_bp.route('/dish/<int:id>/bookmark', methods=['POST'])
def dish_bookmark_toggle(id):
    """Toggle bookmark for a dish (AJAX)"""
    user_email = current_user_email()
    if not user_email:
        return jsonify({'success': False, 'error': 'ログイン経由でのみブックマークできます'}), 403

    dish = Dish.query.get_or_404(id)
    bookmarked = services.toggle_bookmark(user_email, dish.id, current_app.config['BOOKMARK_EXPIRY_DAYS'])
    return jsonify({
        'success': True,
        'bookmarked': bookmarked,
        'bookmark_count': services.get_bookmark_count(user_email)
    })


@main_bp.route('/bookmarks')
def bookmarks_list():
    """JSON list of the current user's active bookmarks, for the nav bell dropdown (AJAX)"""
    user_email = current_user_email()
    rows = services.get_active_bookmarks(user_email)
    return jsonify([{
        'dish_id': b.dish_id,
        'dish_name': b.dish.name,
        'created_at': b.created_at.strftime('%Y-%m-%d'),
        'url': url_for('main.dish_detail', id=b.dish_id)
    } for b in rows])


# =============================================================================
# API Key Issuance (session-protected; the key itself is used against /api/v1)
# =============================================================================

@main_bp.route('/account/api-key', methods=['GET', 'POST'])
def account_api_key():
    """Issue/view a short-lived API key for the logged-in user"""
    user_email = current_user_email()

    if request.method == 'POST':
        if not user_email:
            flash('ログイン経由でのみAPIキーを発行できます', 'error')
            return redirect(url_for('main.account_api_key'))

        raw_key, api_key = services.issue_api_key(
            user_email, current_app.config['API_KEY_EXPIRY_HOURS']
        )
        return render_template('api_key.html',
                               user_email=user_email,
                               raw_key=raw_key,
                               active_key=api_key,
                               expiry_hours=current_app.config['API_KEY_EXPIRY_HOURS'])

    active_key = services.get_active_api_key(user_email) if user_email else None
    return render_template('api_key.html',
                           user_email=user_email,
                           raw_key=None,
                           active_key=active_key,
                           expiry_hours=current_app.config['API_KEY_EXPIRY_HOURS'])


# =============================================================================
# API Endpoints (AJAX, used by the browser UI itself - unchanged)
# =============================================================================

@main_bp.route('/ingredient/search')
def ingredient_search():
    """Search ingredients for autocomplete (AJAX)"""
    q = request.args.get('q', '').strip()

    if not q:
        return jsonify([])

    ingredients = Ingredient.query.filter(
        Ingredient.name.contains(q)
    ).order_by(Ingredient.name).limit(10).all()

    return jsonify([i.to_dict() for i in ingredients])


@main_bp.route("/api/ingredient", methods=["POST"])
def api_ingredient_create():
    """Create ingredient via AJAX (for modal)"""
    data = request.get_json(force=True, silent=True)

    if not data:
        return jsonify({"success": False, "error": "No data provided"}), 400

    name = data.get("name", "").strip()
    category_id = data.get("category_id")

    if not name:
        return jsonify({"success": False, "error": "原材料名は必須です"}), 400

    if not category_id:
        return jsonify({"success": False, "error": "分類は必須です"}), 400

    try:
        ingredient = services.create_ingredient(name, category_id)
    except ValidationError as e:
        return jsonify({"success": False, "error": e.message}), 400

    return jsonify({
        "success": True,
        "ingredient": ingredient.to_dict()
    })


@main_bp.route("/api/categories")
def api_categories():
    """Get all ingredient categories (for modal)"""
    categories = IngredientCategory.query.order_by(IngredientCategory.display_order).all()
    return jsonify([{"id": c.id, "name": c.name} for c in categories])
