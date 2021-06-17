import datetime

import requests
import urllib3
from sqlalchemy import and_

from ec.ext import celery, db
from ec.work_hour.model import WorkHour


@celery.task(name='work_hour_data_synchronize')
def work_hour_data_synchronize():

    for i in range(0, 3):
        now = datetime.datetime.now() - datetime.timedelta(weeks=i)
        year = now.year
        week = now.isocalendar()[1] + 1
        # week = 19
        new_product_work_hours = product_work_hour_data_synchronize(year=year, week=week)
        new_project_work_hours = project_work_hour_data_synchronize(year=year, week=week)

        db.session.add_all(new_product_work_hours + new_project_work_hours)
        db.session.commit()


def product_work_hour_data_synchronize(year, week):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.93 Safari/537.36'}
    url = 'https://pmd.megvii-inc.com/TaskTimeSingleSignOn/api/getTasktimeForYangYi?pmdYear={}&pmdWeekNum={}'. \
        format(year, week)
    urllib3.disable_warnings()
    res = requests.get(url=url, headers=headers, verify=False)
    if res.status_code != 200:
        return

    data = res.json()

    new_product_work_hours = []
    for d in data:
        wh_data = {
            'external_user_id': str(d.get('userId')),
            'username': d.get('loginName'),
            'name': d.get('userName'),
            'department': d.get('deptName'),
            'business_role': d.get('businessRoleName', ''),
            'year': d.get('pmdYear', ''),
            'week': d.get('pmdWeekNum', ''),
            'category': d.get('projectCategoryName', ''),
            'bg': d.get('projectBgName', ''),
            'product_line': d.get('projectLineName', ''),
            'product_family': d.get('projectNationName', ''),
            'project': d.get('projectName', ''),
            'describe': d.get('comments', ''),
            'task_time': d.get('taskTimeDays', ''),
            'type': 0,
            'external_project_id': str(d.get('projectId')),
        }

        old_wh = WorkHour.query.filter(and_(
            WorkHour.external_user_id == str(d.get('userId')),
            WorkHour.year == d.get('pmdYear'),
            WorkHour.week == d.get('pmdWeekNum'),
            WorkHour.type == 0,
            WorkHour.external_project_id == d.get('projectId')

        )).first()

        if old_wh:
            if not old_wh.has_edit:
                old_wh.update(**wh_data)
        else:
            new_product_work_hours.append(WorkHour(**wh_data))

    return new_product_work_hours


def project_work_hour_data_synchronize(year, week):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.93 Safari/537.36'}
    url = 'https://pmd.megvii-inc.com/TaskTimeSingleSignOn/api/getTasktimeForYangYi2?pmdYear={}&pmdWeekNum={}'. \
        format(year, week)
    urllib3.disable_warnings()
    res = requests.get(url=url, headers=headers, verify=False)
    if res.status_code != 200:
        return

    data = res.json()

    new_project_work_hours = []
    for d in data:
        category = d.get('projectCategoryName', '项目研发')
        wh_data = {
            'external_user_id': str(d.get('userId')),
            'username': d.get('loginName'),
            'name': d.get('userName'),
            'department': d.get('deptName'),
            'business_role': d.get('businessRoleName', ''),
            'year': d.get('pmdYear', ''),
            'week': d.get('pmdWeekNum', ''),
            'category': category if category else '项目研发',
            'bg': d.get('projectBgName', ''),
            'product_line': d.get('projectLineName', ''),
            'product_family': d.get('projectNationName', ''),
            'project': d.get('projectName', ''),
            'describe': d.get('comments', ''),
            'task_time': d.get('taskTimeDays', ''),
            'type': 1,
            'external_project_id': str(d.get('projectId')),
        }

        old_wh = WorkHour.query.filter(and_(
            WorkHour.external_user_id == str(d.get('userId')),
            WorkHour.year == d.get('pmdYear'),
            WorkHour.week == d.get('pmdWeekNum'),
            WorkHour.type == 1,
            WorkHour.external_project_id == d.get('projectId')
        )).first()

        if old_wh:
            if not old_wh.has_edit:
                old_wh.update(**wh_data)
        else:
            new_project_work_hours.append(WorkHour(**wh_data))
    return new_project_work_hours

