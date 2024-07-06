import time
import random
import requests
from flask import Flask, render_template, request, redirect, url_for
from flask_bootstrap import Bootstrap5
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Global variables
articles_data = []
favorite_recipes = []


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
                                    "image_url": image,
                                    "time_text": time_text,
                                })
    finally:
        # Quit the driver
        driver.quit()


# Fetch articles once and store them
fetch_articles()

# Flask
app = Flask(__name__)
app.secret_key = "doasnd0asdn80n3n2304b"
Bootstrap5(app)


@app.route("/")
def index():
    random_articles = random.sample(articles_data, 7)
    days_of_week = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    return render_template("index.html", articles=random_articles, days_of_week=days_of_week)

@app.route("/add_to_favorites", methods=["POST"])
def add_to_favorites():
    title = request.form.get("title")
    link = request.form.get("link")
    image_url = None

    # Find the corresponding article in articles_data to get image_url
    for article in articles_data:
        if article["title"] == title and article["link"] == link:
            image_url = article["image_url"]
            break

    favorite_recipes.append({"title": title, "link": link, "image_url": image_url})
    return redirect(url_for('index'))

@app.route("/remove_from_favorites", methods=["POST"])
def remove_from_favorites():
    title = request.form.get("title")
    link = request.form.get("link")

    # Remove the recipe from favorite_recipes
    for recipe in favorite_recipes:
        if recipe["title"] == title and recipe["link"] == link:
            favorite_recipes.remove(recipe)
            break

    return redirect(url_for('favorites'))  # Redirect back to favorites page after removal

@app.route("/favorites")
def favorites():
    return render_template("favorites.html", favorite_recipes=favorite_recipes)

if __name__ == "__main__":
    app.run(debug=True)
