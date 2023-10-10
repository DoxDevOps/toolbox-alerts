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
def send_email_notification(data: any):
    url = config('sendEmailNotificatinForResourceDetailsURL')
    data = json.loads(data)
    if data:
        email_data = {"data": str(data)}
        try:
            response = requests.post(url, data=email_data, headers=headers)
            if response.status_code == 200:
                response_data = response.json()
                print(response_data)
        except Exception as e:
            print(f"An error occurred in fn1: {str(e)}")

@shared_task
def findResouceDetailsWithCloseToFullStorage(zone: any):
    url = config('findResouceDetailsWithCloseToFullStorageURL')
    zone_data = {"data": str(zone)}  # Assuming 'zone' is the relevant data
    try:
        response = requests.post(url, data=zone_data, headers=headers)
        if response.status_code == 200:
            response_data = response.json()
            send_email_notification.delay(response_data)
    except Exception as e:
        print(f"An error occurred in fn2: {str(e)}")

@shared_task
def precursorfindResouceDetailsWithCloseToFullStorage(data: any):
    data = json.loads(data)
    for zone in data:
        findResouceDetailsWithCloseToFullStorage.delay(zone)

@shared_task
def filterSiteResourceDetailListByZone(data: any):
    url = config('filterSiteResourceDetailListByZoneURL')
    try:
        # Define the form data with 'data' as the key and the JSON data as the value
        form_data = data
        response = requests.post(url, data=form_data, headers=headers)
        if response.status_code == 200:
            response_data = response.json()
            precursorfindResouceDetailsWithCloseToFullStorage.delay(response_data)
        else:
            print(f"Request failed with status code {response.status_code}")
            return None
    except Exception as e:
        print(f"An error occurred fn3: {str(e)}")
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
        print(f"An error occurred fn4: {str(e)}")
        return None

