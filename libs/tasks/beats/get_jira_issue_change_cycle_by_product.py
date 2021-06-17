# -*- coding: utf-8 -*-
# Created by Duanwei on 2020/5/20

from sqlalchemy import or_, and_, func
from ec.ext import celery
from ec.jira_manage.model import (
        JiraVersion,
    )
from libs.ci_util.jira_util import JiraUtil
from libs.ci_util.jira_zephyr import JiraZephyr
from libs.jira_util.jira_update import process_jira_issue_data, process_cycle_data


@celery.task(name="get_jira_issue_change_cycle_by_product")
def get_jira_issue_change_cycle_by_product(**kwargs):
    ju = JiraUtil()
    jz = JiraZephyr()
    bug_filter_id_list = []
    case_filter_id_list = []
    bug_filter_id = kwargs.get('bug_filter_id')
    qa_bug_filter_id = kwargs.get('qa_bug_filter_id')
    case_filter_id = kwargs.get('case_filter_id')
    qa_case_filter_id = kwargs.get('qa_case_filter_id')
    jira_id = kwargs.get('jira_id')
    jp_id = kwargs.get('jp_id')

    if bug_filter_id and case_filter_id:
        bug_filter_id_list.append(bug_filter_id)
        case_filter_id_list.append(case_filter_id)
    if qa_bug_filter_id and qa_case_filter_id:
        bug_filter_id_list.append(qa_bug_filter_id)
        case_filter_id_list.append(qa_case_filter_id)

    # 更新jira
    for i in range(len(bug_filter_id_list)):
        # jp_jira_id = jira_id
        bug_filter_jql = "filter=" + bug_filter_id_list[i]
        case_filter_jql = "filter=" + case_filter_id_list[i]
        print('--------', bug_filter_jql, case_filter_jql)
        all_bug_data = ju.get_all_issues_changelog(bug_filter_jql)
        all_case_data = ju.get_all_issues_changelog(case_filter_jql)
        print('----',all_bug_data,all_case_data)
        print("start process issue data...")
        process_jira_issue_data(all_bug_data, jp_id, bug_filter_id_list[i])
        print("start process case data...")
        process_jira_issue_data(all_case_data, jp_id, case_filter_id_list[i])
        # 第三步：根据jira id获取所有对应的所有version id
        jv_all = JiraVersion.query.filter(
            and_(
                JiraVersion.jira_project_id == jp_id, JiraVersion.jira_id == jira_id
            )
        ).with_entities(JiraVersion.version_id, JiraVersion.jira_id)
        jv_all_record = jv_all.all()
        # 第四步：根据version id获取所有cycle
        for jv in jv_all_record:
            jv_id = jv[0]
            jv_jira_id = jv[1]
            all_cycles = jz.get_cycles_by_version(
                project_id=jv_jira_id, version_id=jv_id
            )
            process_cycle_data(all_cycles, jv_jira_id, jv_id, jira_id)
