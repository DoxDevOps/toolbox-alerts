from __future__ import absolute_import, unicode_literals
from celery import shared_task
from decouple import config
import requests
import json

auth_token = config('AUTH_TOKEN')
headers = {
    'Authorization': auth_token
}

@shared_task
def filterSiteResourceDetailListByZone(data: any):
    url = config('filterSiteResourceDetailListByZoneURL')

    try:
        # Define the form data with 'data' as the key and the JSON data as the value
        form_data = data

        response = requests.post(url, data=form_data, headers=headers)

        if response.status_code == 200:
            response_data = response.json()
            print(response_data)

        print(f"Request failed with status code {response.status_code}")
        return None

    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return None

@shared_task
def findUniqueResourceDetails():
    url = config('findUniqueResourceDetailsURL')

    try:
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            data = response.json()
            filterSiteResourceDetailListByZone.delay(data)
        else:
            print(f"Request failed with status code {response.status_code}")
            return None
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return None

