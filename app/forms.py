from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, SelectMultipleField, IntegerField, HiddenField
from wtforms.validators import DataRequired, Length, NumberRange, ValidationError, Optional
from wtforms.widgets import CheckboxInput, ListWidget
from flask import current_app


class MultiCheckboxField(SelectMultipleField):
    """Custom field for multiple checkboxes"""
    widget = ListWidget(prefix_label=False)
    option_widget = CheckboxInput()


class DishForm(FlaskForm):
    """Form for creating/editing a dish"""
    name = StringField('料理名', validators=[
        DataRequired(message='料理名は必須です'),
        Length(min=1, max=100, message='料理名は1〜100文字で入力してください')
    ])

    genre_ids = MultiCheckboxField('料理ジャンル', coerce=int)

    # Use HiddenField for ingredient_ids (comma-separated string from JS)
    ingredient_ids = HiddenField('原材料')

    difficulty = IntegerField('工程（難易度）', validators=[
        DataRequired(message='工程は必須です'),
        NumberRange(min=1, max=5, message='工程は1〜5で選択してください')
    ], default=1)

    memo = TextAreaField('メモ', validators=[
        Optional(),
        Length(max=500, message='メモは500文字以内で入力してください')
    ])

    referrer = HiddenField()

    # Store parsed ingredient IDs (set by route)
    _ingredient_ids_list = []

    def validate_genre_ids(self, field):
        max_genres = current_app.config.get('MAX_GENRES_PER_DISH', 2)
        if field.data and len(field.data) > max_genres:
            raise ValidationError(f'ジャンルは最大{max_genres}個まで選択できます')

    def validate_ingredient_ids(self, field):
        max_ingredients = current_app.config.get('MAX_INGREDIENTS_PER_DISH', 10)
        if self._ingredient_ids_list and len(self._ingredient_ids_list) > max_ingredients:
            raise ValidationError(f'原材料は最大{max_ingredients}個まで選択できます')


class IngredientForm(FlaskForm):
    """Form for creating an ingredient"""
    name = StringField('原材料名', validators=[
        DataRequired(message='原材料名は必須です'),
        Length(min=1, max=100, message='原材料名は1〜100文字で入力してください')
    ])

    category_id = SelectField('分類', coerce=int, validators=[
        DataRequired(message='分類は必須です')
    ])


class SearchForm(FlaskForm):
    """Form for searching dishes"""
    class Meta:
        csrf = False  # Disable CSRF for GET requests

    ingredient_ids = SelectMultipleField('原材料', coerce=int)
    genre_ids = SelectMultipleField('料理ジャンル', coerce=int)
    mode = SelectField('検索モード', choices=[
        ('exact', '完全一致'),
        ('fuzzy', 'あいまい検索')
    ], default='fuzzy')
    page = IntegerField('ページ', default=1)
    per_page = IntegerField('表示件数', default=10)


class DeleteIngredientForm(FlaskForm):
    """Form for deleting an ingredient (with CSRF protection)"""
    pass
