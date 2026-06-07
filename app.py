import csv
import os
import requests
from flask import Flask, render_template, request, redirect, url_for
from dotenv import load_dotenv
from requests_oauthlib import OAuth1



load_dotenv()
app = (Flask(__name__))


api_key = os.environ.get("FATSECRET_API_KEY")
api_secret = os.environ.get("FATSECRET_API_SECRET")
file = 'data_log.csv'

def create_csv():
    if not os.path.exists(file):
        with open(file, mode='w', newline ='') as f:
            writer = csv.writer(f)
            writer.writerow(['meal_type', 'food_item', 'calories', 'protein'])


def get_data(food_query):
    base_url = "https://platform.fatsecret.com/rest/server.api"
    auth = OAuth1(api_key, client_secret=api_secret)

    params = {
        "method": "foods.search",
        "search_expression": food_query.strip(),
        "format": "json",
        "max_results": 1
    }
    
    try:
        response = requests.get(base_url, params=params, auth=auth, timeout=10)
        
        if response.status_code == 200:
            data = response.json() 
            foods_contain = data.get("foods", {})
            food_list = foods_contain.get("food", [])

            if food_list:
                top_match = food_list[0] if isinstance(food_list, list) else food_list
                description = top_match.get("food_description", "")

                processed_result = {
                    "food_name": top_match.get("food_name"),
                    "calories": 100,
                    "fat": 2.0,
                    "carbs": 10.0,
                    "protein": 5.0
                }
                
                if "Calories:" in description:
                    try:
                        parts = description.split("Calories:")
                        cal_string = parts[1].split("kcal")[0].strip()
                        processed_result["calories"] = int(cal_string)
                        
                        protien_string = description.split("Protein:")[1].split("g")[0].strip()
                        processed_result["protein"] = float(protien_string)
                    except Exception:
                        pass
                        
                return processed_result
        return None
    except Exception:
        return None
    
def macro_percentage(calorie_list):
    return list(map(lambda x: round((x /2000) * 100, 1), calorie_list))


@app.route('/')
def index():
    create_csv()
    logs = []
    cals = 0
    with open(file, mode= 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            logs.append(row)
            cals += int(float(row['calories']))

    return render_template('index.html', logs = logs, total_calories=cals )

@app.route('/add-meal', methods=['POST'])
def add_meal():
    meal_type = request.form.get('meal_type')
    food_input = request.form.get('food_input')

    data = get_data(food_input)
    if data:
        cals = data['calories']
        prot = data['protein']
    else:
        cals = 100
        prot = 5.0

    with open(file, mode='a', newline= '') as f:
        writer = csv.writer(f)
        writer.writerow([meal_type, food_input.title(), cals, prot])
    
    return redirect(url_for('index'))

@app.route('/find-alternative', methods=['GET', 'POST'])
def find_alternative():
    if request.method == 'POST':
        user_food = request.form.get('user_food').lower().strip()
        food_data = get_data(user_food)
        
        if food_data:
            swap_rules = {
                "whole milk": "skim milk",
                "milk": "almond milk",
                "rice": "brown rice",
                "steak": "sirloin steak",
                "beef": "lean turkey",
                "butter": "olive oil",
                "chips": "baked pretzels",
                "soda": "diet soda",
                "yogurt": "greek yogurt"
            }
            suggested_search = None
            for bad_food, healthy_alternative in swap_rules.items():
                if bad_food in user_food:
                    suggested_search = user_food.replace(bad_food, healthy_alternative)
                    break   
            if not suggested_search:
                suggested_search = "healthy low calorie {}".format(user_food)           
            alt_data = get_data(suggested_search)
            
            if alt_data:
                return render_template(
                    'results.html', 
                    original=food_data['food_name'], 
                    original_data=food_data, 
                    alt_name=alt_data['food_name'], 
                    alt_data=alt_data
                )
            else:
                return render_template('results.html', error="Could not find a suitable live alternative for '{}'.".format(suggested_search))
        else:
            return render_template('results.html', error="Sorry, {} was not found in the database.".format(user_food))
            
    return render_template('results.html')





if __name__ == '__main__':
    app.run(debug=True)
