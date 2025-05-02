import requests

# Load API key
with open("nvidia_api.txt", "r") as f:
    api_key = f.read().strip()

invoke_url = "https://integrate.api.nvidia.com/v1/chat/completions"
stream = False  # We're not streaming in this version

headers = {
    "Authorization": f"Bearer {api_key}",
    "Accept": "application/json"
}

# Simple category-to-account mapping
ACCOUNT_MAP = {
    "Groceries": "AH Budget Account",
    "Cafe": "Cafe Budget",
    "Shopping": "Fashion Budget",
    "Skincare": "Beauty Budget",
    "Fitness": "Gym & Health",
    "Nightlife": "Going Out Fund",
    "Other": "General Account"
}

def classify_store(store_name):
    prompt = f"""
You are a budgeting assistant. Classify the following store into one of the categories:
Groceries, Cafe, Shopping, Skincare, Fitness, Nightlife, Other.

Store: {store_name}
Category:"""

    payload = {
        "model": "meta/llama-3.1-8b-instruct",  # You can swap to another if needed
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 50,
        "temperature": 0.2,
        "top_p": 0.9,
        "stream": stream
    }

    response = requests.post(invoke_url, headers=headers, json=payload)

    if response.status_code != 200:
        print(f"❌ Error: {response.status_code}")
        print(response.text)
        return "Other"

    content = response.json()
    reply = content["choices"][0]["message"]["content"].strip()
    return reply

def switch_account(category):
    account = ACCOUNT_MAP.get(category, "General Account")
    print(f"🟢 Switching to {account} based on category '{category}'.")

# Test the setup
if __name__ == "__main__":
    test_stores = [
        "Albert Heijn", "Starbucks", "Zara", "Etos", "Normal",
        "Planet Fitness", "De Drie Gezusters", "HEMA", "Basic-Fit"
    ]
    for store in test_stores:
        print(f"\n🛍️ Visiting: {store}")
        category = classify_store(store)
        print(f"🔎 Classified as: {category}")
        switch_account(category)
