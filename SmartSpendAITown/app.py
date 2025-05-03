from flask import Flask, render_template, request, jsonify
from bunq.sdk.context.bunq_context import BunqContext
from bunq import ApiEnvironmentType
from bunq.sdk.context.api_context import ApiContext
from bunq.sdk.model.generated.endpoint import MonetaryAccountBankApiObject, CardDebitApiObject, PaymentApiObject,BunqMeTabResultResponseApiObject,BunqMeTabApiObject, BunqMeTabEntryApiObject, BunqMeTabEntryApiObject, CardApiObject
from bunq.sdk.model.generated.object_ import AmountObject, PointerObject, NotificationFilterObject
from bunq import Pagination
import requests

app = Flask(__name__)
N = 10  # Grid size

grid_data = {'pos': [0, 0]}
store_locations = {
    "2,3": "Starbucks",
    "1,1": "Albert Heijn",
    "5,5": "Zara",
    "7,2": "Etos",
    "8,8": "Spa",
    "3,6": "Tulip Cafe",
    "4,5": "Hair Salon"
}


categories = ["groceries", "cafe", "shopping", "skincare", "fitness", "nightlife", "other"]
category_to_account_id = {}

# Load API key
with open("api.txt", "r") as f:
    api_key = f.read().strip()

# Create an API context for production
api_context = ApiContext.create(
    ApiEnvironmentType.SANDBOX,
    api_key,
    "My Device Description"
)
# Save the API context to a file for future use
#api_context.save("bunq_api_context.conf")
# Load the API context into the SDK
BunqContext.load_api_context(api_context)

# Set up Bunq context
user_context = BunqContext.user_context()
user_id = user_context.user_id
user_person = user_context.user_person
primary_account = user_context.primary_monetary_account
alias_pointer = primary_account.alias[0]

# Get or create bank accounts
accounts = MonetaryAccountBankApiObject.list().value

category_to_account_id = {}
# Output the final mapping
if not accounts:
    for cat in categories:
        print(f"Creating account: {cat}")
        
        new_account_response = MonetaryAccountBankApiObject.create(
            currency="EUR",
            description=cat.capitalize(),
            daily_limit=AmountObject("100.00", "EUR")
        )
        account_id = new_account_response.value
        category_to_account_id[cat] = account_id
else:
    for acc in accounts:
        desc = acc.description.lower()
        for cat in categories:
            if cat in desc:
                category_to_account_id[cat] = acc.id_

# Create virtual card if none exist
cards = []
if not cards:
    card_res = CardDebitApiObject.create(
        second_line="GeoCard AI",
        name_on_card=user_person.display_name,
        alias=alias_pointer,
        type_="MASTERCARD",
        product_type="MASTERCARD_DEBIT",
        order_status="VIRTUAL_DELIVERY"
        )
    card_id = card_res.value.id_
else:
    card_id = cards[0].id_

# NVIDIA classification
with open("nvidia_api.txt", "r") as f:
    API_KEY = f.read().strip()

def classify_store_nvidia(store_name):
    url = "https://integrate.api.nvidia.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {API_KEY}", "Accept": "application/json"
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
        content = response.json()["choices"][0]["message"]["content"].strip().lower()
        print("Raw classification:", content)

        # Extract a valid category from the response
        for category in categories:
            if category in content:
                return category
        return "other"
    except Exception as e:
        print("LLM classification error:", e)
        return "other"

@app.route('/')
def index():
    # Fetch balances to render live accounts
    accounts = MonetaryAccountBankApiObject.list().value
    display_accounts = []
    total = 0.0

    all_accounts = MonetaryAccountBankApiObject.list().value
    display_accounts = []
    total = 0.0

    for acc in all_accounts:
        if acc.status != "ACTIVE":
            continue  # Skip archived/blocked accounts

        balance = float(acc.balance.value)
        total += balance
        display_accounts.append({
            "id": acc.id_,
            "name": acc.description,
            "balance": f"{balance:.2f}",
            "emoji": "💰" if balance > 0 else "⚠️"
        })


    return render_template('map.html',
        grid_size=N,
        pos=grid_data['pos'],
        stores=store_locations,
        net_worth=f"{total:.2f}",
        account=grid_data.get('linked_account', 'None'),
        accounts=display_accounts,
        mood=grid_data.get('mood', "💡 Budget-empowered"),
        log=grid_data.get('log', [])
    )

@app.route('/move', methods=['POST'])
def move():
    key = request.json.get('key')
    move_map = {'W': (-1, 0), 'A': (0, -1), 'S': (1, 0), 'D': (0, 1)}
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
            account_id = category_to_account_id.get(category, primary_account.id_)

            CardApiObject.update(
                card_id=card_id,
                monetary_account_id_fallback=account_id
            )

            grid_data['linked_account'] = category.capitalize()
            grid_data['log'] = [f"Visited {store} → {category}. Card linked to {category.capitalize()}."]
        else:
            grid_data['log'] = []

    return jsonify({
        'pos': grid_data['pos'],
        'account': grid_data.get('linked_account', 'None')
    })

if __name__ == '__main__':
    app.run(debug=True)
