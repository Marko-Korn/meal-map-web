import time
import random
import os
import requests
from flask import Flask, render_template, request, redirect, url_for, session
from flask_bootstrap import Bootstrap5
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_sqlalchemy import SQLAlchemy

# Global variables
articles_data = []
favorite_recipes = []
# Flask
app = Flask(__name__)
app.secret_key = os.environ['SECRET_KEY']
Bootstrap5(app)
# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
# SQLAlchemy configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
db = SQLAlchemy(app)


# Define User model
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    favorite_recipes = db.relationship('FavoriteRecipe', backref='user', lazy=True)


# Define FavoriteRecipe model
class FavoriteRecipe(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    link = db.Column(db.String(200), nullable=False)
    image_url = db.Column(db.String(200), nullable=True)  # Allow NULL if images can be missing
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def create_app():
    # Create all tables
    with app.app_context():
        db.create_all()

    return app

# Selenium
def fetch_articles():
    global articles_data  # Ensure we're modifying the global variable
    URL = "https://www.valio.fi/reseptihaku/?ruokalajityyppi=paaruoat"

    # Selenium
    driver = webdriver.Chrome()
    try:
        driver.get(URL)
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "vl-block-valio-search__content"))
        )

        # Function to scroll down the page
        def scroll_down():
            # Scroll down using JavaScript
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            # Wait for some time to load new content
            time.sleep(2)  # Adjust sleep time as needed

        # Scroll down 5 times to load more articles
        for _ in range(5):
            scroll_down()

        # Get the updated HTML after scrolling
        html = driver.page_source

        soup = BeautifulSoup(html, "html.parser")
        main_content = soup.find("main", id="site-content", class_="site-content")

        if main_content:
            block_root = main_content.find("article", class_="block-root")
            if block_root:
                wp_block = block_root.find("div", class_="wp-block-evermade-valio-search-kitchen vl-block-valio-search")
                if wp_block:
                    content_div = wp_block.find("div", class_="vl-block-valio-search__content")
                    if content_div:
                        results_grid = content_div.find("div", class_="vl-block-valio-search__results-grid recipes")
                        if results_grid:
                            articles = results_grid.find_all("article", class_="vl-block-recipe-card recipes")
                            for article in articles:
                                title = article.find("h3").text.strip()
                                link = article.find("a")["href"]
                                true_link = f"https://www.valio.fi/reseptit{link}"
                                image = article.find("img")["src"] if article.find("img") else None
                                time_text = article.find('span', class_='vl-block-recipe-card__time').text.strip()
                                articles_data.append({
                                    "title": title,
                                    "link": true_link,
                                    "image_url": image,  # Ensure image_url is correctly assigned
                                    "time_text": time_text,
                                })
    finally:
        # Quit the driver
        driver.quit()


# Fetch articles once and store them
fetch_articles()

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        # Check if username is already taken
        if User.query.filter_by(username=username).first():
            return 'Username already taken. Please choose another.'
        # Create new user
        new_user = User(username=username, password=password)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and password == user.password:
            login_user(user)
            session['logged_in'] = True
            return redirect(url_for('index'))
        else:
            return 'Invalid username or password'
    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    session.pop('logged_in', None)
    return redirect(url_for('index'))


@app.route("/")
def index():
    random_articles = random.sample(articles_data, 7)
    days_of_week = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    return render_template("index.html", articles=random_articles, days_of_week=days_of_week)


@app.route("/add_to_favorites", methods=["POST"])
@login_required
def add_to_favorites():
    title = request.form.get("title")
    link = request.form.get("link")
    image_url = request.form.get("image_url")  # Capture image_url from the form
    print(image_url)

    # Create a FavoriteRecipe instance
    new_favorite = FavoriteRecipe(title=title, link=link, image_url=image_url, user_id=current_user.id)

    # Add to database within app context
    with app.app_context():
        db.session.add(new_favorite)
        db.session.commit()

    return redirect(url_for('index'))


@app.route("/remove_from_favorites", methods=["POST"])
@login_required
def remove_from_favorites():
    favorite_id = request.form.get("favorite_id")

    # Find and delete the FavoriteRecipe instance
    favorite_recipe = FavoriteRecipe.query.get(favorite_id)
    db.session.delete(favorite_recipe)
    db.session.commit()

    return redirect(url_for('favorites'))


@app.route("/favorites")
def favorites():
    return render_template("favorites.html", favorite_recipes=favorite_recipes)


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)
