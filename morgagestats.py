import requests
from bs4 import BeautifulSoup
from creds import username, password
from statistics import mean
from weds import webflow_bearer_token
from datetime import datetime
import locale

# Set locale to Norwegian
try:
    locale.setlocale(locale.LC_TIME, 'nb_NO.utf8')
except locale.Error:
    print("Norwegian locale not available. Using default locale.")

# Finansportalen URL
fin_url = "https://www.finansportalen.no/services/feed/v3/bank/boliglan.atom"

# Webflow API details
webflow_api_url = "https://api.webflow.com/v2/collections/669f728ab3c40ae0d0050db0/items/669f796b6b83e870137ea733/live"

def calculate_effective_rate(nominal_rate, termingebyr, etableringsgebyr, loan_amount=2000000):
    annual_fee = termingebyr * 12
    interest_amount = (loan_amount * nominal_rate) / 100
    effective_rate = (interest_amount + annual_fee + etableringsgebyr) * 100 / loan_amount
    return effective_rate

def print_averages(category, nominal, effective):
    print(f"Average interest rate for rentebinding {category}:")
    print(f"  Nominal: {nominal:.2f}%")
    print(f"  Effective: {effective:.2f}%")

# Norwegian month names
norwegian_months = [
    "januar", "februar", "mars", "april", "mai", "juni",
    "juli", "august", "september", "oktober", "november", "desember"
]

response = requests.get(fin_url, auth=(username, password))

if response.status_code == 200:
    soup = BeautifulSoup(response.content, 'xml')
    entries = soup.find_all('entry')

    rates = {0: {'nominal': [], 'effective': []},
             3: {'nominal': [], 'effective': []},
             5: {'nominal': [], 'effective': []},
             10: {'nominal': [], 'effective': []}}

    for entry in entries:
        try:
            nominal_rate = float(entry.find('f:nominell_rente_1_a').text)
            binding_years = int(entry.find('f:rentebinding_ar').text)
            termingebyr = float(entry.find('f:termingebyr_1_a').text)
            etableringsgebyr = float(entry.find('f:etableringsgebyr').text)
            
            effective_rate = calculate_effective_rate(nominal_rate, termingebyr, etableringsgebyr)
            
            if binding_years not in rates:
                binding_years = 0
            
            rates[binding_years]['nominal'].append(nominal_rate)
            rates[binding_years]['effective'].append(effective_rate)
            
        except (ValueError, AttributeError):
            print(f"Warning: Could not process an entry due to missing or invalid data")

    # Calculate averages and print to terminal
    all_nominal = [rate for sublist in rates.values() for rate in sublist['nominal']]
    all_effective = [rate for sublist in rates.values() for rate in sublist['effective']]

    print_averages("variable", mean(rates[0]['nominal']), mean(rates[0]['effective']))
    print_averages("3 years", mean(rates[3]['nominal']), mean(rates[3]['effective']))
    print_averages("5 years", mean(rates[5]['nominal']), mean(rates[5]['effective']))
    print_averages("10 years", mean(rates[10]['nominal']), mean(rates[10]['effective']))
    print_averages("all loans", mean(all_nominal), mean(all_effective))

    # Get current date in Norwegian format
    now = datetime.now()
    current_date = f"Sist oppdatert: {now.day}. {norwegian_months[now.month - 1]} {now.year}"

    # Prepare data for Webflow update
    payload = {
        "fieldData": {
            "fastrente-10-ar-effektiv-rente": f"{mean(rates[10]['effective']):.2f}",
            "fastrente-10-ar-rente": f"{mean(rates[10]['nominal']):.2f}",
            "fastrente-5-ar-rente": f"{mean(rates[5]['nominal']):.2f}",
            "fastrente-3-ar-rente": f"{mean(rates[3]['nominal']):.2f}",
            "gjsnitt-nominell-rente": f"{mean(all_nominal):.2f}",
            "gjsnitt-effektiv-rente": f"{mean(all_effective):.2f}",
            "fastrente-3-ar-effektiv-rente": f"{mean(rates[3]['effective']):.2f}",
            "fastrente-5-ar-effektiv-rente": f"{mean(rates[5]['effective']):.2f}",
            "sist-oppdatert": current_date
        }
    }

    print("\nValues being sent to Webflow:")
    for key, value in payload['fieldData'].items():
        print(f"  {key}: {value}")

    # Update Webflow item
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "authorization": f"Bearer {webflow_bearer_token}"
    }

    webflow_response = requests.patch(webflow_api_url, json=payload, headers=headers)

    if webflow_response.status_code == 200:
        print("\nWebflow item updated successfully")
        print(f"Response: {webflow_response.text}")
    else:
        print(f"\nFailed to update Webflow item. Status code: {webflow_response.status_code}")
        print(f"Response: {webflow_response.text}")

else:
    print(f"Failed to access the Finansportalen URL. Status code: {response.status_code}")