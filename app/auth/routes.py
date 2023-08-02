from app.auth import bp
from flask_login import login_required, login_user, logout_user, current_user
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db
from flask import render_template, request, redirect, url_for, session, flash

from app.models.user import User


@bp.route('/login', methods=['GET', 'POST'])
def login():
    session.permanent = True
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        remember = True if request.form.get('remember') else False
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            # login_user(user)
            login_user(user, remember=remember)
            return redirect(url_for('main.index'))
        else:
            # return "Incorrect username or password"
            flash('Неверный логин или пароль!')
            return redirect(request.url)
    return render_template('auth/login.html')


@bp.route('/signup', methods=['GET', 'POST'])
# TODO: Временно сделал регистрацию доступной только для пользователя вошедшего в систему
@login_required
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = generate_password_hash(request.form['password'])
        user = User(username=username, password=password)
        db.session.add(user)
        db.session.commit()
        return redirect(url_for('main.index'))
    return render_template('auth/signup.html')


@bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))


@bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    users = User.query.all()

    # TODO: Сделать валидацию нового пароля (нужно ввести 2 раза и что бы два поля совпали)
    # Форма уже сделана в auth.py ChangePasswordForm()

    if request.method == 'POST':
        # Get the current and new passwords from the form
        current_password = request.form['current_password']
        new_password = request.form['new_password']

        # Check if the current password is correct
        if not check_password_hash(current_user.password, current_password):
            flash('Неверный текущий пароль!')
            return redirect(request.url)

        # Update the user's password in the database
        current_user.password = generate_password_hash(new_password)
        db.session.commit()

        return redirect(url_for('auth.profile'))
    return render_template('auth/profile.html', users=users)
