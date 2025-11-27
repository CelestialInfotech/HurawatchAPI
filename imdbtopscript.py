


import requests
from bs4 import BeautifulSoup
import json
import os
import re
import time
import random
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE_URL = "https://hurawatchzz.tv"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36"
}

OUTPUT_FILE = "imdb.json"


# --------------------------------------------------------
# Load existing movies (JSON LIST)
# --------------------------------------------------------
def load_existing():
    if not os.path.exists(OUTPUT_FILE):
        return []
    try:
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []


# --------------------------------------------------------
# Save full JSON list
# --------------------------------------------------------
def save_full_json(data):
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    print("✔ Saved full list:", OUTPUT_FILE)


# --------------------------------------------------------
# Parse movie card from page
# --------------------------------------------------------
def parse_movie_card(item):
    title_tag = item.select_one(".film-name a")
    title = title_tag.text.strip() if title_tag else ""
    url = BASE_URL + title_tag["href"] if title_tag else ""

    img = item.select_one("img.film-poster-img")
    image = img.get("data-src") if img else ""

    quality = item.select_one(".film-poster-quality")
    qa = quality.text.strip() if quality else ""

    type_ = item.select_one(".fdi-type")
    typ = type_.text.strip() if type_ else ""

    items = item.select(".fdi-item")

    season = items[0].text if len(items) > 0 else ""
    episode = items[1].text if len(items) > 1 else ""

    yr = item.select_one(".fdi-item")
    year = yr.text.strip() if yr else ""

    
    du = item.select_one(".fdi-duration")
    duration = du.text.strip() if du else ""

    score = random.randint(0, 180)
    like = random.randint(0, 10000)
    dislike = random.randint(0, 10000)

    return {
        "title": title,
        "url": url,
        "image": image,
        "quality": qa,
        "type": typ,
        "year": "" if "SS" in year else year,
        "season": "" if typ == "Movie" else season,
        "episode": "" if typ == "Movie" else episode,
        "duration": duration,
        "score": score,
        "like": like,
        "dislike": dislike,
    }


# --------------------------------------------------------
# Movie page details (description, rating, etc.)
# --------------------------------------------------------
def scrape_movie_details(url):
    print(" → Fetching:", url)
    r = requests.get(url, headers=HEADERS, timeout=10)
    soup = BeautifulSoup(r.text, "html.parser")

    data = {}


    title = soup.select_one(".heading-name a")
    data["title_detail"] = title.text.strip() if title else ""

    cover_div = soup.select_one(".w_b-cover")
    dimage = ""
    if cover_div and "style" in cover_div.attrs:
        match = re.search(r'url\(["\']?(.*?)["\']?\)', cover_div["style"])
        if match:
            dimage = match.group(1)
    data["dimage"] = dimage

    # eps_items = soup.select(".eps-item")
    # episodes = []

    # for eps in eps_items:
    #     ep_id = eps.get("data-id")
    #     if ep_id:                 # <-- MUST be inside loop
    #         episodes.append(ep_id)

    # data["episodes"] = episodes


    desc = soup.select_one(".description")
    data["description"] = desc.text.strip() if desc else ""

    data["country"] = [a.text.strip() for a in soup.select(".elements .row-line:nth-of-type(1) a")]
    data["genre"] = [a.text.strip() for a in soup.select(".elements .row-line:nth-of-type(2) a")]
    data["production"] = [a.text.strip() for a in soup.select(".elements .row-line:nth-of-type(4) a")]
    data["casts"] = [a.text.strip() for a in soup.select(".elements .row-line:nth-of-type(5) a")]

    rel = soup.select_one(".elements .row-line:nth-of-type(3)")
    data["released"] = rel.text.replace("Released:", "").strip() if rel else ""

    return data


# --------------------------------------------------------
# Extract ID from movie URL
# --------------------------------------------------------
def extract_movie_id(url):
    match = re.search(r"(\d+)$", url)  # last number at end of URL
    return match.group(1) if match else None


# --------------------------------------------------------
# Main scraping function (fast)
# --------------------------------------------------------
def scrape_paginated_movies_fast():
    all_movies = load_existing()
    visited = set(movie["url"] for movie in all_movies)

    page = 1
    while True:
        page_url = f"{BASE_URL}/top-imdb?type=all&page={page}"
        print(f"\n=== PAGE {page} ===")

        try:
            r = requests.get(page_url, headers=HEADERS, timeout=10)
        except Exception as e:
            print("Error fetching page:", e)
            break

        soup = BeautifulSoup(r.text, "html.parser")
        items = soup.select(".flw-item")

        if not items:
            print("END — No more pages.")
            break

        new_movies = []

        for item in items:
            basic = parse_movie_card(item)
            if basic["url"] in visited:
                continue
            new_movies.append(basic)
            visited.add(basic["url"])

        # Fetch movie details concurrently
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {executor.submit(scrape_movie_details, m["url"]): m for m in new_movies}
            for future in as_completed(futures):
                basic = futures[future]
                try:
                    details = future.result()
                except Exception as e:
                    print("Error fetching details:", basic["url"], e)
                    details = {}
                movie_id = extract_movie_id(basic["url"])
                final = {**basic, **details, "movie_id": movie_id}
                all_movies.append(final)
                print("✔ Added:", basic["title"])

        # Save once per page
        save_full_json(all_movies)

        page += 1
        # Optional small sleep between pages
        time.sleep(0.3)


# --------------------------------------------------------
# RUN SCRIPT
# --------------------------------------------------------
if __name__ == "__main__":
    scrape_paginated_movies_fast()
    print("\n✔ FINISHED")
    print("All data saved →", OUTPUT_FILE)
