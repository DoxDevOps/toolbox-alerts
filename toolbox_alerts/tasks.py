from __future__ import absolute_import, unicode_literals
from celery import shared_task
from decouple import config
import requests

@shared_task
def findUniqueResourceDetails():
    # Get the URL and Authorization token from the configuration file
    url = config('findUniqueResourceDetailsURL')
    auth_token = config('AUTH_TOKEN')  # Replace with your actual auth token

    print(url)
    print(auth_token)

    # Create headers with Authorization
    headers = {
        'Authorization': auth_token
    }

    try:
        # Make the GET request with the headers
        response = requests.get(url, headers=headers)

        # Check the response status code
        if response.status_code == 200:
            # Successful request, you can process the response data here
            data = response.json()
            print(data)
        else:
            # Handle non-200 response codes here
            print(f"Request failed with status code {response.status_code}")
            return None
    except Exception as e:
        # Handle exceptions (e.g., network errors) here
        print(f"An error occurred: {str(e)}")
        return None

