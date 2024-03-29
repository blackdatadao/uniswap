import time,requests,json

user_input = 0

# Button to append the input to the list and save it
def send_id_to_server(user_input):
    url = 'http://42.192.17.155/realised_id'
    headers = {'Content-Type': 'application/json'}

    try:
        # GET request to fetch the current list
        response = requests.get(url)
        if response.status_code == 200:
                data = response.json()
                data.append(user_input)
                # POST request to send the updated list back to the server
                post_response = requests.post(url, json=data, headers=headers)
                post_response.raise_for_status()  # Check for HTTP errors
                print("Data successfully sent to server.")
        else:
            print('Error:', response.status_code)
    except json.JSONDecodeError:
        print('Error: Invalid JSON')
    except requests.exceptions.HTTPError as e:
        print('HTTP error occurred:', e)
    except requests.exceptions.RequestException as e:
        print('Request failed:', e)

c=1