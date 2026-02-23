import requests

def test_open_position_api():
    # URL of the API endpoint on the worker instance
    url = "http://3.70.230.123:8000/api/open_position/"
    
    # Sample data payload - adjust according to your API's expected format
    data = {
        "pair": "EUR/USD",
        "operation": "open",
        "volume": 1.0,
        "direction": "long",
        # Add other necessary fields according to your specific needs
    }
    
    # Make the POST request
    response = requests.post(url, json=data)
    
    # Check if the request was successful
    if response.status_code == 200:
        print("API call successful.")
        print("Response data:", response.json())
    else:
        print("API call failed.")
        print("Status code:", response.status_code)
        print("Response data:", response.text)

if __name__ == "__main__":
    test_open_position_api()
