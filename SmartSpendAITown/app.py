from flask import Flask, render_template, request, jsonify
import requests

app = Flask(__name__)

N = 10  # Grid size
grid_data = {
    'pos': [0, 0],
    'log': []
}

store_locations = {
    "2,3": "Starbucks",
    "1,1": "Albert Heijn",
    "5,5": "Zara",
    "7,2": "Etos",
    "8,8": "Planet Fitness",
    "3,6": "De Drie Gezusters"
}


account_map = {
    "Groceries": "AH Budget Account",
    "Cafe": "Cafe Budget",
    "Shopping": "Fashion Budget",
    "Skincare": "Beauty Budget",
    "Fitness": "Gym & Health",
    "Nightlife": "Going Out Fund",
    "Other": "General Account"
}

with open("/Users/francescabrzoskowski/geocard/nvidia_api.txt", "r") as f:
    API_KEY = f.read().strip()

def classify_store_nvidia(store_name):
    url = "https://integrate.api.nvidia.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Accept": "application/json"
    }
    prompt = f"""
    You are a budgeting assistant. Classify the following store into one of the categories:
    Groceries, Cafe, Shopping, Skincare, Fitness, Nightlife, Other.

    Store: {store_name}
    Category:"""
    payload = {
        "model": "meta/llama-3.1-8b-instruct",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 50,
        "temperature": 0.2,
        "top_p": 0.9,
        "stream": False
    }
    try:
        response = requests.post(url, headers=headers, json=payload)
        return response.json()["choices"][0]["message"]["content"].strip()
    except Exception:
        return "Other"

@app.route('/')
def index():
    return render_template('map.html', grid_size=N, pos=grid_data['pos'], stores=store_locations, log=grid_data['log'])

@app.route('/move', methods=['POST'])
def move():
    key = request.json.get('key')
    move_map = {
        'W': (-1, 0),
        'A': (0, -1),
        'S': (1, 0),
        'D': (0, 1)
    }
    if key in move_map:
        dy, dx = move_map[key]
        y, x = grid_data['pos']
        new_y = max(0, min(N - 1, y + dy))
        new_x = max(0, min(N - 1, x + dx))
        grid_data['pos'] = [new_y, new_x]

       
        store_key = f"{new_y},{new_x}"
        if store_key in store_locations:
            store = store_locations[store_key]
            category = classify_store_nvidia(store)
            account = account_map.get(category, "General Account")
            grid_data['log'].append(f"👟 Visited {store} → {category}. Switched to {account}.")
#        else:
#           grid_data['log'].append(f"➡️ Moved to ({new_y},{new_x})")

    return jsonify({'pos': grid_data['pos'], 'log': grid_data['log'][-5:]})

if __name__ == '__main__':
    app.run(debug=True)
