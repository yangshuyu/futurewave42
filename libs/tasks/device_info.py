from ec.ext import celery
from libs.pb.deployment import DeviceInfo


@celery.task
def device_info(ip, username, password):
    extra_vars = {
        'ansible_user': username,
        'ansible_password': password,
    }
    ad = DeviceInfo(hosts=[ip], extra_vars=extra_vars)
    ad.run()


