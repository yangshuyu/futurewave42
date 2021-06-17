# -*- coding: utf-8 -*-
# Created by Duanwei on 2020/5/20

from sqlalchemy import or_, and_, func
from ec.ext import celery
from ec.jira_manage.model import (
    JiraProject,
    JiraVersion,
    )
from libs.ci_util.jira_util import JiraUtil
from libs.ci_util.jira_zephyr import JiraZephyr
from libs.jira_util.jira_update import process_jira_issue_data, process_cycle_data


@celery.task(name="get_qa_jira_issue_change_cycle")
def get_qa_jira_issue_change_cycle():
    ju = JiraUtil()
    jz = JiraZephyr()
    # 获取所有jira project的bug_filter_id,case_filter_id,version_id_list
    jp_all = JiraProject.query.with_entities(
        JiraProject.id,
        JiraProject.bug_filter_id,
        JiraProject.case_filter_id,
        JiraProject.jira_id,
        JiraProject.qa_bug_filter_id,
        JiraProject.qa_case_filter_id,
    )
    jp_all_record = jp_all.all()
    # 第一步：根据bug_filter_id获取所有bug和change history
    # 第二步：根据case_filter_id获取所有用例
    for jp in jp_all_record:
        # print(jp)
        jp_id = jp[0]
        jp_jira_id = jp[3]
        jp_qa_bug_filter_id = jp[4]
        jp_qa_case_filter_id = jp[5]
        if (jp_qa_bug_filter_id):
            qa_bug_filter_jql = "filter=" + jp_qa_bug_filter_id
            all_qa_bug_data = ju.get_all_issues_changelog(qa_bug_filter_jql)
            print("start process issue data...")
            process_jira_issue_data(all_qa_bug_data, jp_id, jp_qa_bug_filter_id)
        if (jp_qa_case_filter_id):
            qa_case_filter_jql = "filter=" + jp_qa_case_filter_id
            all_qa_case_data = ju.get_all_issues_changelog(qa_case_filter_jql)
            print("start process case data...")
            process_jira_issue_data(all_qa_case_data, jp_id, jp_qa_case_filter_id)
        jv_all = JiraVersion.query.filter(
            and_(
                JiraVersion.jira_project_id == jp_id, JiraVersion.jira_id == jp_jira_id
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
            process_cycle_data(all_cycles, jv_jira_id, jv_id, jp_id)