from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from sqlalchemy import func
from app import db
from app.models import Dish, Ingredient, IngredientCategory, DishGenre
from app.forms import DishForm, IngredientForm, SearchForm, DeleteIngredientForm

main_bp = Blueprint('main', __name__)


def get_ingredients_by_category():
    """Get all ingredients grouped by category"""
    categories = IngredientCategory.query.order_by(IngredientCategory.display_order).all()
    return categories


def get_all_genres():
    """Get all genres"""
    return DishGenre.query.all()


def get_all_ingredients():
    """Get all ingredients"""
    return Ingredient.query.order_by(Ingredient.category_id, Ingredient.display_order).all()


# =============================================================================
# Search Pages
# =============================================================================

@main_bp.route('/')
def search():
    """Search page (search mode)"""
    categories = get_ingredients_by_category()
    genres = get_all_genres()
    return render_template('search.html',
                           categories=categories,
                           genres=genres,
                           mode='search')


@main_bp.route('/edit')
def edit_mode():
    """Search page (edit mode)"""
    categories = get_ingredients_by_category()
    genres = get_all_genres()

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
    ingredient_ids_str = request.args.get('ingredient_ids', '')
    genre_ids_str = request.args.get('genre_ids', '')
    mode = request.args.get('mode', 'fuzzy')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', current_app.config['ITEMS_PER_PAGE'], type=int)
    view_mode = request.args.get('view_mode', 'search')  # search or edit

    ingredient_ids = [int(x) for x in ingredient_ids_str.split(',') if x.strip().isdigit()]
    genre_ids = [int(x) for x in genre_ids_str.split(',') if x.strip().isdigit()]

    # Build query
    query = Dish.query

    # Filter by genres
    if genre_ids:
        query = query.filter(Dish.genres.any(DishGenre.id.in_(genre_ids)))

    # Filter by ingredients
    if ingredient_ids:
        if mode == 'exact':
            # Exact match: dish must have ALL specified ingredients
            for ing_id in ingredient_ids:
                query = query.filter(Dish.ingredients.any(Ingredient.id == ing_id))
        else:
            # Fuzzy match: dish must have ANY of specified ingredients
            query = query.filter(Dish.ingredients.any(Ingredient.id.in_(ingredient_ids)))

    # Order by relevance (number of matching ingredients) for fuzzy search
    if mode == 'fuzzy' and ingredient_ids:
        # Subquery to count matching ingredients
        query = query.order_by(Dish.updated_at.desc())
    else:
        query = query.order_by(Dish.updated_at.desc())

    # Paginate
    dishes = query.paginate(page=page, per_page=per_page, error_out=False)

    categories = get_ingredients_by_category()
    genres = get_all_genres()

    template = 'edit_mode.html' if view_mode == 'edit' else 'search.html'

    return render_template(template,
                           categories=categories,
                           genres=genres,
                           dishes=dishes,
                           selected_ingredient_ids=ingredient_ids,
                           selected_genre_ids=genre_ids,
                           search_mode=mode,
                           mode=view_mode)


# =============================================================================
# Dish Detail / Form Pages
# =============================================================================

@main_bp.route('/dish/<int:id>')
def dish_detail(id):
    """Dish detail page (read-only)"""
    dish = Dish.query.get_or_404(id)
    referrer = request.args.get('referrer', request.referrer or url_for('main.search'))
    return render_template('dish_detail.html', dish=dish, referrer=referrer)


def parse_comma_separated_ids(value):
    """Parse comma-separated string into list of integers"""
    if not value:
        return []
    return [int(x) for x in value.split(',') if x.strip().isdigit()]


@main_bp.route('/dish/new', methods=['GET', 'POST'])
def dish_new():
    """Create new dish"""
    form = DishForm()

    # Set choices for genres
    all_genres = get_all_genres()
    form.genre_ids.choices = [(g.id, g.name) for g in all_genres]

    if request.method == 'POST':
        # Parse comma-separated ingredient_ids from hidden field
        ingredient_ids_str = request.form.get('ingredient_ids', '')
        ingredient_ids = parse_comma_separated_ids(ingredient_ids_str)
        form._ingredient_ids_list = ingredient_ids

        if form.validate_on_submit():
            dish = Dish(
                name=form.name.data,
                difficulty=form.difficulty.data,
                memo=form.memo.data
            )

            # Add genres
            for genre_id in form.genre_ids.data:
                genre = DishGenre.query.get(genre_id)
                if genre:
                    dish.genres.append(genre)

            # Add ingredients
            for ingredient_id in ingredient_ids:
                ingredient = Ingredient.query.get(ingredient_id)
                if ingredient:
                    dish.ingredients.append(ingredient)

            db.session.add(dish)
            db.session.commit()

            flash('料理を登録しました', 'success')
            return redirect(url_for('main.edit_mode'))

    categories = get_ingredients_by_category()

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
    all_genres = get_all_genres()
    form.genre_ids.choices = [(g.id, g.name) for g in all_genres]

    if request.method == 'GET':
        # Pre-populate form with existing data
        form.genre_ids.data = [g.id for g in dish.genres]
        form.ingredient_ids.data = ','.join(str(i.id) for i in dish.ingredients)
        form.referrer.data = request.args.get('referrer', request.referrer or url_for('main.edit_mode'))
    else:
        # Parse comma-separated ingredient_ids from hidden field
        ingredient_ids_str = request.form.get('ingredient_ids', '')
        ingredient_ids = parse_comma_separated_ids(ingredient_ids_str)
        form._ingredient_ids_list = ingredient_ids

        if form.validate_on_submit():
            dish.name = form.name.data
            dish.difficulty = form.difficulty.data
            dish.memo = form.memo.data

            # Update genres
            dish.genres.clear()
            for genre_id in form.genre_ids.data:
                genre = DishGenre.query.get(genre_id)
                if genre:
                    dish.genres.append(genre)

            # Update ingredients
            dish.ingredients.clear()
            for ingredient_id in ingredient_ids:
                ingredient = Ingredient.query.get(ingredient_id)
                if ingredient:
                    dish.ingredients.append(ingredient)

            db.session.commit()

            flash('料理を更新しました', 'success')

            # Return to referrer or detail page
            referrer = form.referrer.data
            if referrer and 'dish/' in referrer:
                return redirect(url_for('main.dish_detail', id=dish.id))
            return redirect(referrer or url_for('main.edit_mode'))

    categories = get_ingredients_by_category()
    genres = get_all_genres()

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
    db.session.delete(dish)
    db.session.commit()

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
        # Check for duplicate name
        existing = Ingredient.query.filter_by(name=form.name.data).first()
        if existing:
            flash('同じ名前の原材料が既に存在します', 'error')
        else:
            # Get max display_order for the category
            max_order = db.session.query(func.max(Ingredient.display_order)).filter_by(
                category_id=form.category_id.data
            ).scalar() or 0

            ingredient = Ingredient(
                name=form.name.data,
                category_id=form.category_id.data,
                display_order=max_order + 1
            )
            db.session.add(ingredient)
            db.session.commit()

            flash('原材料を登録しました', 'success')

            # Return to referrer
            referrer = request.form.get('referrer') or request.referrer
            if referrer:
                return redirect(referrer)
            return redirect(url_for('main.ingredients'))

    categories = IngredientCategory.query.order_by(IngredientCategory.display_order).all()
    return render_template('ingredient_register.html',
                           form=form,
                           categories=categories)


@main_bp.route('/ingredients')
def ingredients():
    """Ingredient management page"""
    category_id = request.args.get('category_id', type=int)
    categories = get_ingredients_by_category()

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
    dish_count = ingredient.dishes.count()
    dish_names = [d.name for d in ingredient.dishes.limit(5).all()]

    return jsonify({
        'count': dish_count,
        'dishes': dish_names,
        'has_more': dish_count > 5
    })


@main_bp.route('/ingredient/<int:id>/delete', methods=['POST'])
def ingredient_delete(id):
    """Delete an ingredient"""
    ingredient = Ingredient.query.get_or_404(id)

    # The CASCADE will handle removing the ingredient from dishes
    db.session.delete(ingredient)
    db.session.commit()

    flash(f'「{ingredient.name}」を削除しました', 'success')
    return redirect(url_for('main.ingredients'))


# =============================================================================
# API Endpoints (AJAX)
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
