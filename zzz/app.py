from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
# Ключ для защиты сессий пользователей
app.secret_key = 'super_temporary_secret_key_for_coursework'

# --- НАСТРОЙКА ПОДКЛЮЧЕНИЯ К POSTGRESQL ---
DB_USER = 'postgres'
DB_PASSWORD = '1234'  # ⚠️ УКАЖИТЕ ВАШ ПАРОЛЬ ОТ POSTGRESQL ИЗ DBEAVER
DB_HOST = 'localhost'
DB_PORT = '5432'
DB_NAME = 'train_schedule_db'

app.config['SQLALCHEMY_DATABASE_URI'] = f'postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- МОДЕЛИ ДАННЫХ ---

# Модель пользователя
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

# Модель рейса электрички
class TrainRoute(db.Model):
    __tablename__ = 'train_routes'
    id = db.Column(db.Integer, primary_key=True)
    train_number = db.Column(db.String(10), nullable=False)
    station_from = db.Column(db.String(100), nullable=False)
    station_to = db.Column(db.String(100), nullable=False)
    departure_time = db.Column(db.String(5), nullable=False)
    arrival_time = db.Column(db.String(5), nullable=False)
    duration = db.Column(db.String(20), nullable=False)
    price = db.Column(db.Integer, nullable=False)


# --- МАРШРУТЫ ПРИЛОЖЕНИЯ (ROUTES) ---

# Главная страница (Поиск и вывод расписания)
@app.route('/', methods=['GET', 'POST'])
def index():
    routes = []
    search_from = ""
    search_to = ""
    current_user = session.get('username')
    
    if request.method == 'POST':
        search_from = request.form.get('station_from', '').strip()
        search_to = request.form.get('station_to', '').strip()
        
        routes = TrainRoute.query.filter(
            TrainRoute.station_from.ilike(f"%{search_from}%"),
            TrainRoute.station_to.ilike(f"%{search_to}%")
        ).all()
    else:
        routes = TrainRoute.query.all()

    return render_template('index.html', routes=routes, search_from=search_from, search_to=search_to, current_user=current_user)


# Панель администратора (Доступ только для franfri)
@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if session.get('username') != 'franfri':
        flash('Доступ запрещен! Вы не являетесь администратором.', 'error')
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        train_number = request.form.get('train_number').strip()
        station_from = request.form.get('station_from').strip()
        station_to = request.form.get('station_to').strip()
        departure_time = request.form.get('departure_time').strip()
        arrival_time = request.form.get('arrival_time').strip()
        duration = request.form.get('duration').strip()
        price = int(request.form.get('price', 0))
        
        new_route = TrainRoute(
            train_number=train_number, station_from=station_from, station_to=station_to,
            departure_time=departure_time, arrival_time=arrival_time, duration=duration, price=price
        )
        db.session.add(new_route)
        db.session.commit()
        flash(f'Рейс №{train_number} добавлен!', 'success')
        return redirect(url_for('admin'))
        
    routes = TrainRoute.query.all()
    return render_template('admin.html', routes=routes)


# Удаление рейса из админки
@app.route('/admin/delete/<int:route_id>')
def delete_route(route_id):
    if session.get('username') != 'franfri':
        flash('Доступ запрещен!', 'error')
        return redirect(url_for('index'))
        
    route = TrainRoute.query.get(route_id)
    if route:
        db.session.delete(route)
        db.session.commit()
        flash('Рейс успешно удален из базы.', 'success')
    return redirect(url_for('admin'))


# Регистрация
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username').strip()
        password = request.form.get('password')
        
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Пользователь с таким именем уже существует!', 'error')
            return redirect(url_for('register'))
        
        hashed_password = generate_password_hash(password)
        new_user = User(username=username, password_hash=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        
        flash('Регистрация успешна! Войдите в систему.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')


# Вход (Авторизация)
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username').strip()
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password):
            session['username'] = user.username
            flash('Вы успешно вошли в систему!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Неверный логин или пароль', 'error')
            return redirect(url_for('login'))
    return render_template('login.html')


# Выход из аккаунта
@app.route('/logout')
def logout():
    session.pop('username', None)
    flash('Вы вышли из системы.', 'info')
    return redirect(url_for('index'))


# Инициализация БД (Вызывается автоматически при запуске)
def init_db():
    with app.app_context():
        db.create_all()
        
        # Проверяем и создаем учетную запись администратора franfri
        admin_user = User.query.filter_by(username='franfri').first()
        if not admin_user:
            hashed_admin_pw = generate_password_hash('1234')
            franfri_admin = User(username='franfri', password_hash=hashed_admin_pw)
            db.session.add(franfri_admin)
            db.session.commit()
            print("Администратор franfri / 1234 создан в БД!")
            
        # Заполняем базу начальными данными, если таблица пуста
        if not TrainRoute.query.first():
            test_routes = [
                TrainRoute(train_number="6102", station_from="Москва (Ярославский)", station_to="Сергиев Посад", departure_time="08:20", arrival_time="09:45", duration="1ч 25м", price=240),
                TrainRoute(train_number="6304", station_from="Москва (Ярославский)", station_to="Пушкино", departure_time="09:05", arrival_time="09:50", duration="45м", price=140),
                TrainRoute(train_number="7104", station_from="Москва (Ярославский)", station_to="Сергиев Посад", departure_time="10:00", arrival_time="11:10", duration="1ч 10м", price=320)
            ]
            db.session.bulk_save_objects(test_routes)
            db.session.commit()

if __name__ == '__main__':
    init_db()
    app.run(debug=True)