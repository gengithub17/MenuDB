from datetime import datetime
from app import db


# Association tables for many-to-many relationships
dish_genre_relations = db.Table(
    'dish_genre_relations',
    db.Column('dish_id', db.Integer, db.ForeignKey('dishes.id', ondelete='CASCADE'), primary_key=True),
    db.Column('genre_id', db.Integer, db.ForeignKey('dish_genres.id'), primary_key=True)
)

dish_ingredient_relations = db.Table(
    'dish_ingredient_relations',
    db.Column('dish_id', db.Integer, db.ForeignKey('dishes.id', ondelete='CASCADE'), primary_key=True),
    db.Column('ingredient_id', db.Integer, db.ForeignKey('ingredients.id', ondelete='CASCADE'), primary_key=True)
)


class IngredientCategory(db.Model):
    """Ingredient category (fixed, user cannot add)"""
    __tablename__ = 'ingredient_categories'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    display_order = db.Column(db.Integer, nullable=False, default=0)

    # Relationship
    ingredients = db.relationship('Ingredient', backref='category', lazy='select',
                                  order_by='Ingredient.display_order')

    def __repr__(self):
        return f'<IngredientCategory {self.name}>'


class DishGenre(db.Model):
    """Dish genre (fixed, user cannot add)"""
    __tablename__ = 'dish_genres'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)

    def __repr__(self):
        return f'<DishGenre {self.name}>'


class Ingredient(db.Model):
    """Ingredient"""
    __tablename__ = 'ingredients'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    category_id = db.Column(db.Integer, db.ForeignKey('ingredient_categories.id'), nullable=False)
    display_order = db.Column(db.Integer, nullable=False, default=0)

    def __repr__(self):
        return f'<Ingredient {self.name}>'

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'category_id': self.category_id
        }


class Dish(db.Model):
    """Dish"""
    __tablename__ = 'dishes'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False)
    difficulty = db.Column(db.Integer, nullable=False, default=1)
    memo = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    genres = db.relationship('DishGenre', secondary=dish_genre_relations,
                             backref=db.backref('dishes', lazy='dynamic'))
    ingredients = db.relationship('Ingredient', secondary=dish_ingredient_relations,
                                  backref=db.backref('dishes', lazy='dynamic'))

    __table_args__ = (
        db.CheckConstraint('difficulty >= 1 AND difficulty <= 5', name='check_difficulty_range'),
    )

    def __repr__(self):
        return f'<Dish {self.name}>'

    @property
    def genre_ids(self):
        return [g.id for g in self.genres]

    @property
    def ingredient_ids(self):
        return [i.id for i in self.ingredients]

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'difficulty': self.difficulty,
            'memo': self.memo,
            'genres': [{'id': g.id, 'name': g.name} for g in self.genres],
            'ingredients': [{'id': i.id, 'name': i.name} for i in self.ingredients]
        }
