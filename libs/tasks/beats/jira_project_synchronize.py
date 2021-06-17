import time

import jira
import requests
from bs4 import BeautifulSoup
from requests.auth import HTTPBasicAuth
from sqlalchemy import and_

from ec.ext import celery, db
from ec.jira_manage.extend import JiraGongDanGroup, JiraGongDanProject


@celery.task(name='jira_project_synchronize')
def jira_project_synchronize():
    ja = jira.JIRA(basic_auth=("sng-test-bot", "CjEcg#Vp"), options={'server': 'https://jira.megvii-inc.com/'})

    meta = ja.editmeta('CORESP-1170')

    # inspect the meta to get the field you want to look at
    try:
        field = meta['fields']['customfield_12272']
        jira_biz_project_synchronize(field)
    except Exception as e:
        print(e)

    try:
        field = meta['fields']['customfield_12273']
        jira_core_project_synchronize(field)
    except Exception as e:
        print(e)


def jira_biz_project_synchronize(field):
    group_values = field.get('allowedValues')

    for group_value in group_values:
        old_group = JiraGongDanGroup.query.filter(and_(
            JiraGongDanGroup.jira_id == group_value.get('id'),
            JiraGongDanGroup.value == group_value.get('value'),
        )).first()
        if not old_group:
            group = JiraGongDanGroup(
                jira_id=group_value.get('id'),
                value=group_value.get('value'),
                type=0
            )
            db.session.add(group)
            db.session.commit()
            group_id = group.id
        else:
            group_id = old_group.id

        for project_value in group_value.get('children'):
            old_project = JiraGongDanProject.query.filter(and_(
                JiraGongDanProject.jira_id == project_value.get('id'),
                JiraGongDanProject.value == project_value.get('value'),
                JiraGongDanProject.group_id == group_id
            )).first()

            if not old_project:
                project = JiraGongDanProject(
                    jira_id=project_value.get('id'),
                    value=project_value.get('value'),
                    group_id=group_id,
                    type=0
                )
                db.session.add(project)
                db.session.commit()


def jira_core_project_synchronize(field):
    group_values = field.get('allowedValues')

    for group_value in group_values:
        old_group = JiraGongDanGroup.query.filter(and_(
            JiraGongDanGroup.jira_id == group_value.get('id'),
            JiraGongDanGroup.value == group_value.get('value'),
        )).first()
        if not old_group:
            group = JiraGongDanGroup(
                jira_id=group_value.get('id'),
                value=group_value.get('value'),
                type=1
            )
            db.session.add(group)
            db.session.commit()
            group_id = group.id
        else:
            group_id = old_group.id

        for project_value in group_value.get('children'):
            old_project = JiraGongDanProject.query.filter(and_(
                JiraGongDanProject.jira_id == project_value.get('id'),
                JiraGongDanProject.value == project_value.get('value'),
                JiraGongDanProject.group_id == group_id
            )).first()

            if not old_project:
                project = JiraGongDanProject(
                    jira_id=project_value.get('id'),
                    value=project_value.get('value'),
                    group_id=group_id,
                    type=1
                )
                db.session.add(project)
                db.session.commit()

