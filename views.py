from email import message
from threading import Thread
from django.shortcuts import render, redirect
from .models import Site, SiteModuleVersion, QuarterySiteModuleVersion, Watch, SiteUptime, SiteResourceDetail, SiteSystemService, SystemService
from apps.models import App, AppModule
from users.models import Profile
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from .utils import github, pagination, qr_func
from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.urls import reverse
import logging
from api.views import insert_into_SiteResourceDetailModel, meta_data
from sites.utils import notification_service, cron
from django.shortcuts import get_object_or_404
from api.utils.api import filterForQuarterySiteModuleVersions, filterForSiteSystemServices
from .models import Zone, District, Site, SiteResourceDetail
import json
from django.db.models import Count, F,OuterRef,Subquery, Prefetch, Max
from django.db.models.functions import Coalesce

def convert_to_gigabytes(input_str):
    # Convert the string to uppercase
    input_str = input_str.upper()

    # Check if the string has 'T' or 'G' suffix
    if 'T' in input_str:
        # Convert terabytes to gigabytes
        gigabytes = float(input_str.replace('T', '')) * 1024
    elif 'G' in input_str:
        # Extract the numeric part and convert to gigabytes
        gigabytes = float(input_str.replace('G', ''))
    else:
        # Return the input value as it is
        gigabytes = float(input_str)

    return gigabytes

@login_required
def get_sites(request):

    profile = Profile.objects.get(user=request.user)
    sites = Site.objects.all()
    page_obj = pagination.paginator(sites, 30, 1)
    sites_hhd_storage = []
    switch_status = "checked"
    allowed_districts = profile.district.all()
    districts_and_their_sites = []

    for allowedDistrict in allowed_districts:
        district_obj = {
            'name': allowedDistrict,
            'sites': []
        }

        for site in sites:
            if allowedDistrict == site.district:
                if site not in district_obj['sites']:
                    district_obj['sites'].append(site)

        
        if district_obj['sites']:
            districts_and_their_sites.append(district_obj)


    for site in sites:
        try:
            siteResourceDetail = SiteResourceDetail.objects.filter(site=site).latest('created_on')
            sites_hhd_storage.append(
                {
                    "site_name" : site.name,
                    "hdd_used_in_percentiles" : int(siteResourceDetail.hdd_used_in_percentiles)
                }
            )
        except:
            sites_hhd_storage.append(
                {
                    "site_name" : site.name,
                    "hdd_used_in_percentiles" : 0
                }
            )
        try:
            watch = Watch.objects.get(user=request.user, site=site)

            if watch.value == "unwatch":
                switch_status = ""

        except Exception as e:
            switch_status = ""
        
    return render(request, "sites/sites_listing.html", {
        "user": request.user,
        "sites": sites,  # page_obj,
        "allowed_districts": allowed_districts,
        "districts_and_their_sites": districts_and_their_sites,
        "sites_hhd_storage": sites_hhd_storage,
            "switch_status_for_all": switch_status,
        })


@login_required
def get_site(request, pk):
    """[summary]

    Args:
        request ([type]): [description]
        uuid ([type]): [description]
    """
    site = Site.objects.get(pk=pk)

    try:
        siteResourceDetail = SiteResourceDetail.objects.filter(site=site).latest('created_on')
    except Exception as e:
        siteResourceDetail = {}

    module_versions = filterForQuarterySiteModuleVersions(
                        QuarterySiteModuleVersion.objects.filter(site=pk))
    
    siteSystemServices = filterForSiteSystemServices(
                          SiteSystemService.objects.filter(site=pk))

    ping_result = SiteUptime.objects.filter(site=pk).last()

    try:
        watch = Watch.objects.get(user=request.user, site=pk)

        if watch.value == "watch":
            switch_status = "checked"
        
        else:
            switch_status = ""

    except Exception as e:
        switch_status = ""

    return render(request, "sites/site_details.html", {
        "user": request.user,
        "site": site,
        "available_apps": site.apps.all(),
        "module_versions": module_versions,
        "switch_status": switch_status,
        "ping": ping_result,
        "siteResourceDetail": siteResourceDetail,
        "siteSystemServices": siteSystemServices
    })


@login_required
def follow_site(request, pk):

    user = request.user
    site = Site.objects.get(pk=pk)

    if user in site.watching.all():
        site.watching.remove(user)
    else:
        site.watching.add(user)

    watch, created = Watch.objects.get_or_create(user=user, site=site)

    ui_res = "unchecked"

    if not created:
        if watch.value == "watch":
            watch.value = "unwatch"
        else:
            watch.value = "watch"
            ui_res = "checked"

    watch.save()

    return HttpResponse(ui_res)

@login_required
def follow_sites(request):
    profile = Profile.objects.get(user=request.user)
    switch_status = request.GET['switch_status']
    allowed_districts = profile.district.all()
    sites = Site.objects.all()
    user = request.user

    for site in sites:
        if  site.district in allowed_districts:
                if user in site.watching.all():
                        site.watching.remove(user)
                else:
                    site.watching.add(user)

                watch, created = Watch.objects.get_or_create(user=user, site=site)

                ui_res = "unchecked"

                if not created:
                    if (switch_status == "unchecked"):
                         watch.value = "watch"
                         ui_res = "checked"
                    elif (switch_status == "checked"):
                        watch.value = "unwatch"

                    watch.save()

    return HttpResponse(ui_res)


@login_required
def update_app_version(request, site_id, app_id):

    tags = {}

    modules = AppModule.objects.filter(app=app_id)

    for module in modules:
        url = f"https://api.github.com/repos/{module.github_name_repo}/tags"
        tags[module.name] = github.get_tags(url)

    user = request.user

    profile = user.profile

    allowed_districts = profile.district.all()

    site = Site.objects.get(pk=site_id)

    app = App.objects.get(pk=app_id)

    message = ""
    success = ""

    if request.method == "POST":

        if site.district not in allowed_districts:
            message = "Looks like you do not have privilages to record a version for this site"

        else:
            for module in modules:

                obj, created = SiteModuleVersion.objects.update_or_create(
                    site=site,
                    app=app,
                    module=module,
                    defaults={'version': request.POST[module.name]},
                )

                success = "Successfully updated the version"

    return render(request, "sites/update_app_version.html", {
        "user": request.user,
        "app": app,
        "site": site,
        "modules": modules,
        "tags": tags,
        "allowed_districts": allowed_districts,
        "message": message,
        "success": success
    })

from django.views.decorators.csrf import csrf_exempt
# @login_required
@csrf_exempt
def validate_qr(request):

    template = "sites/qr/error.html"

    if request.method != "POST":
        return render(request, template, {"error": "Not really sure how you got here. Please scan a QR first!"})

    data = qr_func.str_to_dict(request.POST['data'])


    if not qr_func.validate(data=data):

        return render(request, template, {"error": "Something wrong with the data supplied"})

    try:

        site = Site.objects.get(uuid=data["uuid"])

        # check if serial_number attribute is present
        if "serial_number" in data:
            # check if site from db has a blank/empty field
            if site.serial_number:
                # check if serial numbers match
                if site.serial_number != data["serial_number"]:
                    # returns an error to user if scanned serial does not match stored serial number
                    return render(request, template, {"error": "Scanned serial number for this host does not match"})

            else:
                try:
                    # check if another facility has the same serial number before saving
                    if isDuplicateSiteSerialNumber(serialNumber=data["serial_number"]):
                        return render(request, template, {"error": "Scanned serial number for this host already exists for another facility"}) 
                    else:
                        # storing facility host serial id
                        site.serial_number = data["serial_number"]
                        site.save()
                except:
                   print("err: failded to save serial number")

        # if  system_utilization attribute is present
        if "system_utilization" in data:
            try:
                insert_into_SiteResourceDetailModel(site, data['system_utilization'])
            except Exception as e:
                print("error", str(e))
            
            # check condition
            if data['system_utilization']['hdd_used_in_percentiles']:
                hhd_in_percentages = str(data['system_utilization']['hdd_used_in_percentiles'])
                hhd_in_percentages = hhd_in_percentages.replace('%','')
                if int(hhd_in_percentages) >= 80:
                    hdd_total_storage = data['system_utilization']['hdd_total_storage']
                    hdd_used_storage  = data['system_utilization']['hdd_used_storage']
                    hdd_remaining_storage = data['system_utilization']['hdd_remaining_storage']
                    hdd_used_in_percentiles = data['system_utilization']['hdd_used_in_percentiles']
                    # Send email and sms notification
                    # notification_service.sendNotification(site=site)

                    # for background processing
                    # xThread = Thread(target=notification_service.sendNotification,
                    #                   args=(site,
                    #                         hdd_total_storage,
                    #                         hdd_used_storage,
                    #                         hdd_remaining_storage,
                    #                         hdd_used_in_percentiles,
                    #                     )
                    #                 )
                    # xThread.start()
        
        try:
            if "system_service" in data:

                if data['system_service']['MySQL']:
                    for systemService in SystemService.objects.all():
                        if systemService.name.lower == str(data['system_service']['MySQL']).lower:
                            SiteSystemService.objects.create(
                                site=site,
                                systemService=systemService,
                                status=data['system_service'][systemService.name]
                            )

                for systemService in SystemService.objects.all():
                    try:
                        if data['system_service'][systemService.name]:
                            SiteSystemService.objects.create(
                                site=site,
                                systemService=systemService,
                                status=data['system_service'][systemService.name]
                            )
                    except Exception as e:
                        # You can handle the exception here or simply pass if you want to ignore it.
                        # For example, you can log the error or print a message for debugging purposes.
                        pass
                    
        except Exception as e:
            print("error", str(e))

    except Exception as e:
        print(f"Failed to get object. More info on the exception: {str(e)}")
        logging.error(f"Failed to get object. More info on the exception: {str(e)}")
        return render(request, template, {"error": "Something went wrong"})
    
    else:

        if "app_dirs" in data:
            
            for app_dir in data['app_dirs']:
                module_name = meta_data.dirs_map_to_module[app_dir]
                module_obj = get_object_or_404(AppModule, name=module_name)
                app = module_obj.app

                QuarterySiteModuleVersion.objects.create(
                    site=site,
                    app=app,
                    module=module_obj,
                    quarter= qr_func.get_current_quarter(),
                    version= data['app_dirs'][app_dir]['version']
                )
        
        else:

            try:
                app = App.objects.get(pk=data['app_id'])
                modules = AppModule.objects.filter(app=data['app_id'])

            except Exception as e:
                return render(request, template, {"Something went wrong": str(e)})

            for module in modules:

                obj, created = SiteModuleVersion.objects.update_or_create(
                    site=site,
                    app=app,
                    module=module,
                    defaults={
                        'version': data["module"][str(module)]},
                )
                
                # successive storing of scanned site versions
                QuarterySiteModuleVersion.objects.create(
                    site=site,
                    app=app,
                    module=module,
                    quarter= qr_func.get_current_quarter(),
                    version= data["module"][str(module)]
                )
             
        return HttpResponseRedirect(reverse("sites:view_site", args=[site.id]))

def isDuplicateSiteSerialNumber(serialNumber):
    try:
        site_duplicate_serial = Site.objects.get(serial_number=serialNumber)
        if site_duplicate_serial.serial_number:
            # List of known duplicate serial numbers
            known_duplicates = ["3CKK1J3", "PF1PB9GN", "PF1PHPCA", "PF1NEZPG", "PF1NE1NZ", "PF1NK5YV"]
            
            if site_duplicate_serial.serial_number in known_duplicates:
                return False
            else:
                return True
    except:
        return False

@csrf_exempt
def start_schedule(request):
    """ starts schedules jobs
    """

    if (
        request.headers["Authorization"]
        == "yyJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoxLCJleHAiOjE2MzY0MjQ0NjR9.iRlIMoZgYUQxZMq-CZiLusUfPyofkLCA8djNbOaJYT0"
    ):
        #  invoke schedule method
        def do_work():
            cron.start()

        thread = Thread(target=do_work)
        thread.start()

        return JsonResponse({"success": "job started"}, safe=False)

    else:
        return JsonResponse(
            {"status": "error", "message": "authorization failed"}, safe=False
        )
    
@login_required
def reports(request):
    return render(request, 'sites/reports.html', {})

@login_required
def storage_report(request):
    # Retrieve storage data for the report and pass it to the template
    zones = Zone.objects.all()

    # Create a list to hold storage data for each zone
    zone_data = []

    for zone in zones:
        # Fetch districts for each zone
        districts = zone.district_set.all()

        # Create a dictionary to store storage data for each district in the zone
        zone_district_data = {
            'zone_name': zone.name,
            'districts': []
        }

        for district in districts:
            # Fetch sites for each district
            sites = district.site_set.all()

            # Create a dictionary to store storage data for each site in the district
            district_site_data = {
                'district_name': district.name,
                'sites': []
            }

            for site in sites:
                associated_apps = site.apps.all()


                try:
                    # Fetch SiteResourceDetail data for each site
                    site_resource_detail = SiteResourceDetail.objects.filter(site=site).last()

                    # Create a dictionary to store storage data for the site
                    site_data = {
                        'site_name': site.name,
                        'os_name': site_resource_detail.os_name,
                        'cpu_utilization': site_resource_detail.cpu_utilization,
                        'hdd_total_storage': convert_to_gigabytes(site_resource_detail.hdd_total_storage),
                        'hdd_remaining_storage': convert_to_gigabytes(site_resource_detail.hdd_remaining_storage),
                        'hdd_used_storage': convert_to_gigabytes(site_resource_detail.hdd_used_storage),
                        'hdd_used_in_percentiles': site_resource_detail.hdd_used_in_percentiles,
                        'app_name': [app.name for app in associated_apps]
                    }

                    # Add site_data to district_site_data
                    district_site_data['sites'].append(site_data)
                except Exception as e:
                    print(str(e))


            # Add district_site_data to zone_district_data
            zone_district_data['districts'].append(district_site_data)

        # Add zone_district_data to zone_data
        zone_data.append(zone_district_data)

    
    _apps_ = []
    for app in App.objects.all():
        _apps_.append(
            {'app_name': app.name,}
        )

    # Convert the zone_data to JSON format
    # zone_data_json = json.dumps(zone_data)


    return render(request, 'sites/storage_report.html', {
        'zone_data': zone_data,
        'apps': _apps_,
    })

@login_required
def site_up_time(request):
    # return render(request, 'sites/underdevelopment.html', {})
    zones = Zone.objects.all()
    zone_data = []

    for zone in zones:
        districts = zone.district_set.all()

        zone_district_data = {
            'zone_name': zone.name,
            'districts': []
        }

        for district in districts:
            # Fetch sites for each district
            sites = district.site_set.all()

            district_site_data = {
                'district_name': district.name,
                'sites': []
            }

            for site in sites:
                try:
                    site_up_time = SiteUptime.objects.filter(site=site).last()

                    site_data = {
                    'site_name': site.name,
                    'is_alive': str(site_up_time.is_alive).lower(),
                    'created_on': str(site_up_time.created_on)
                    }

                    district_site_data['sites'].append(site_data)
                except Exception as e:
                    print(str(e))

            zone_district_data['districts'].append(district_site_data)

        zone_data.append(zone_district_data)

    return render(request, 'sites/site_up_time_chart.html', {
        'zone_data': zone_data
    })

@login_required
def site_app_versions(request):
    return render(request, 'sites/underdevelopment.html', {})

@login_required
def system_services_report(request):
    return render(request, 'sites/underdevelopment.html', {})
    zones = Zone.objects.all()
    systemServices = SystemService.objects.all()
    zone_data = []

    for zone in zones:
        districts = zone.district_set.all()

        zone_district_data = {
            'zone_name': zone.name,
            'districts': []
        }

        for district in districts:
            # Fetch sites for each district
            sites = district.site_set.all()

            district_site_data = {
                'district_name': district.name,
                'sites': []
            }

            for site in sites:
                site_system_services = {}
                try:
                    for system_service in systemServices:
                        status = ""
                        created_on = ""
                        try:
                            site_system_service = SiteSystemService.objects.filter(site=site, systemService=system_service).last()
                            status = str(site_system_service.status).lower()
                            created_on = str(site_system_service.updated_on)
                        except Exception as e:
                            # print(str(e))
                            site_system_services[system_service.name] = {
                                                "name": system_service.name,
                                                'site_name': site.name,
                                                "status": 'not_running',
                                                "created_on": ''
                                            }
                            pass
                        if status != "":
                            print(status)
                            site_system_services[system_service.name] = {
                                                "name": system_service.name,
                                                'site_name': site.name,
                                                "status": status,
                                                "created_on": created_on
                                            }
                except Exception as e:
                    print(str(e))

                site_data = {
                    'site_name': site.name,
                    'system_service': site_system_services
                }

                print(site_system_services)

                if site_system_services:
                    district_site_data['sites'].append(site_data)

            zone_district_data['districts'].append(district_site_data)

        zone_data.append(zone_district_data)

    return render(request, 'sites/site_system_service_stat_chart.html', {
        'zone_data': zone_data
    })


@csrf_exempt
def find_Unique_Resource_Details(request):
    """ returns a list of unique resource details
    """

    if (
        request.headers["Authorization"]
        == "yyJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoxLCJleHAiOjE2MzY0MjQ0NjR9.iRlIMoZgYUQxZMq-CZiLusUfPyofkLCA8djNbOaJYT0"
    ):
        data = notification_service.findUniqueResourceDetails()
        return JsonResponse({"data":  data}, safe=False)
