from __future__ import absolute_import, unicode_literals
from celery import shared_task
from decouple import config
import requests

auth_token = config('AUTH_TOKEN')
headers = {
    'Authorization': auth_token
}

@shared_task
def filterSiteResourceDetailListByZone(data: any):
    url = config('filterSiteResourceDetailListByZoneURL')

    try:
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            data = response.json()
            print(data)
        else:
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
        else:
            print(f"Request failed with status code {response.status_code}")
            return None
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return None

