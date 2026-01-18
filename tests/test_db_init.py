"""
Test database initialization script.

This script loads test data from test_data.json into the database.
Run with: python -m tests.test_db_init
"""

import json
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models import Ingredient, Dish, DishGenre


def load_test_data():
    """Load test data from JSON file into the database."""
    # Get the path to test_data.json
    test_data_path = os.path.join(os.path.dirname(__file__), 'test_data.json')

    with open(test_data_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Check if data already exists
    if Ingredient.query.first() is not None:
        print("Test data already exists. Skipping initialization.")
        return

    print("Loading test data...")

    # Load ingredients
    for ing_data in data['ingredients']:
        ingredient = Ingredient(
            id=ing_data['id'],
            name=ing_data['name'],
            category_id=ing_data['category_id'],
            display_order=ing_data['display_order']
        )
        db.session.add(ingredient)

    db.session.commit()
    print(f"  Loaded {len(data['ingredients'])} ingredients")

    # Load dishes
    for dish_data in data['dishes']:
        dish = Dish(
            id=dish_data['id'],
            name=dish_data['name'],
            difficulty=dish_data['difficulty'],
            memo=dish_data.get('memo', '')
        )

        # Add genres
        for genre_id in dish_data.get('genre_ids', []):
            genre = DishGenre.query.get(genre_id)
            if genre:
                dish.genres.append(genre)

        # Add ingredients
        for ingredient_id in dish_data.get('ingredient_ids', []):
            ingredient = Ingredient.query.get(ingredient_id)
            if ingredient:
                dish.ingredients.append(ingredient)

        db.session.add(dish)

    db.session.commit()
    print(f"  Loaded {len(data['dishes'])} dishes")

    print("Test data loaded successfully!")


def main():
    """Main entry point."""
    # Create app with testing configuration
    app = create_app('testing')

    with app.app_context():
        # Drop and recreate all tables for a clean slate
        db.drop_all()
        db.create_all()

        # Initialize master data (categories and genres)
        from app import init_master_data
        init_master_data()

        # Load test data
        load_test_data()


if __name__ == '__main__':
    main()
