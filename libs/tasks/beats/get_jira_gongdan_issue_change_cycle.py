# -*- coding: utf-8 -*-
# Created by Duanwei on 2020/5/20

import json
from ec.ext import db
import requests
from sqlalchemy import or_, and_, func, desc
from ec.ext import celery
from ec.jira_manage.extend import JiraGongDanPatch
from ec.jira_manage.model import (
    JiraGongdan,
    JiraGongdanIssue,
    JiraGongdanIssueChangeHistory,
    JiraGongDanIssueField,
)
from libs.ci_util.jira_util import JiraUtil
from libs.ci_util.jira_zephyr import JiraZephyr


@celery.task(name="get_jira_gongdan_issue_change_cycle")
def get_jira_gongdan_issue_change_cycle():
    update_jira_gong_dan_field()
    ju = JiraUtil()
    jz = JiraZephyr()
    # 获取所有jira project的bug_filter_id,case_filter_id,version_id_list
    jp_all = JiraGongdan.query.with_entities(JiraGongdan.id, JiraGongdan.bug_filter_id)
    jp_all_record = jp_all.all()
    # 第一步：根据bug_filter_id获取所有bug和change history
    # 第二步：根据case_filter_id获取所有用例
    print(jp_all_record)
    for jp in jp_all_record:
        # print(jp)
        jp_id = jp[0]
        jp_bug_filter_id = jp[1]
        bug_filter_jql = "filter=" + jp_bug_filter_id
        all_bug_data = ju.get_all_issues_changelog(bug_filter_jql)
        print("start process issue data...")
        try:
            process_jira_issue_data(all_bug_data, jp_id, jp_bug_filter_id)
        except Exception as e:
            print(str(e))
            raise e
        update_gongdan_issue_duration(jp_id, jp_bug_filter_id)


def update_jira_gong_dan_field():
    from jira import JIRA
    ja = JIRA(basic_auth=("sng-test-bot", "CjEcg#Vp"), options={'server': 'https://jira.megvii-inc.com/'})
    # get an example issue that has the field you're interested in
    sst_meta = ja.editmeta('SSTSP-946')
    biz_solution_values = [v['value'] for v in sst_meta['fields']['customfield_11878']['allowedValues']]
    attribute_values = [v['value'] for v in sst_meta['fields']['customfield_11829']['allowedValues']]
    reason_values = [v['value'] for v in sst_meta['fields']['customfield_11613']['allowedValues']]
    core_meta = ja.editmeta('CORESP-1163')
    core_solution_values = [v['value'] for v in core_meta['fields']['customfield_12274']['allowedValues']]
    biz_dict = {'issue_solution': biz_solution_values, 'issue_attribute': attribute_values,
                'issue_cause': reason_values}
    core_dict = {'issue_solution': core_solution_values, 'issue_attribute': attribute_values,
                 'issue_cause': reason_values}
    for i in biz_dict.keys():
        try:
            biz_gong_dan_id = JiraGongdan.query.filter(JiraGongdan.jira_key == 'SSTSP').first()
            jf = JiraGongDanIssueField.query.filter(
                and_(
                    JiraGongDanIssueField.jira_gong_dan_id == biz_gong_dan_id.id,
                    JiraGongDanIssueField.field_name == i,
                )).first()
            if jf:
                jf.update(**{"filed_options": biz_dict[i]})
            else:
                JiraGongDanIssueField.add(**{"jira_gong_dan_id": biz_gong_dan_id.id, "field_name": i,
                                                 "field_options": biz_dict[i]})
        except Exception as e:
            print(e)
    for i in core_dict.keys():
        try:
            core_gong_dan_id = JiraGongdan.query.filter(JiraGongdan.jira_key == 'CORESP').first()
            jf = JiraGongDanIssueField.query.filter(
                and_(
                    JiraGongDanIssueField.jira_gong_dan_id == core_gong_dan_id.id,
                    JiraGongDanIssueField.field_name == i,
                )).first()
            if jf:
                jf.update(**{"filed_options": biz_dict[i]})
            else:
                JiraGongDanIssueField.add(**{"jira_gong_dan_id": core_gong_dan_id.id, "field_name": i,
                                                 "field_options": core_dict[i]})
        except Exception as e:
            print(e)


def process_jira_issue_data(data, jira_gongdan_id, filter_id):
    from ec.jira_manage.extend import JiraGongDanComment
    from jira import JIRA
    ja = JIRA(basic_auth=("sng-test-bot", "CjEcg#Vp"), options={'server': 'https://jira.megvii-inc.com/'})
    new_issue_id_list = [issue.id for issue in data]
    # print(data)
    print("new id list length: %s" % str(len(new_issue_id_list)))
    old_issue_id_list = (
        JiraGongdan.query.filter(
            and_(
                JiraGongdanIssue.jira_gongdan_id == jira_gongdan_id,
                JiraGongdanIssue.filter_id == filter_id,
            )
        )
            .with_entities(JiraGongdanIssue.issue_id)
            .all()
    )
    old_issue_id_list = list(set([s[0] for s in old_issue_id_list]))
    # 增加的
    # add_list = list(set(new_issue_id_list).difference(set(old_issue_id_list)))
    # 减少的
    del_list = list(set(old_issue_id_list).difference(set(new_issue_id_list)))
    if del_list:
        JiraGongdanIssue.query.filter(JiraGongdanIssue.issue_id.in_(del_list)).delete(
            synchronize_session=False
        )
        JiraGongdanIssueChangeHistory.query.filter(
            JiraGongdanIssueChangeHistory.issue_id.in_(del_list)
        ).delete(synchronize_session=False)
        # 删除评论和patch数据
        JiraGongDanPatch.query.filter(JiraGongDanPatch.gong_dan_issue_id.in_(del_list)).delete(
            synchronize_session=False)
        JiraGongDanComment.query.filter(
            JiraGongDanComment.gong_dan_issue_id.in_(del_list)).delete(synchronize_session=False)

        db.session.commit()
    for issue in data:
        # 添加bug，case
        issue_data = dict()
        issue_data["jira_gongdan_id"] = jira_gongdan_id
        issue_data["filter_id"] = filter_id
        issue_data["issue_key"] = issue.key
        issue_data["issue_id"] = issue.id
        issue_data["issue_url"] = issue.self
        if issue.fields.resolution:
            issue_data["issue_resolution_name"] = issue.fields.resolution.name
            issue_data["issue_resolution_id"] = issue.fields.resolution.id
        if issue.fields.assignee:
            issue_data["issue_assignee"] = issue.fields.assignee.key
            issue_data["issue_assignee_email"] = issue.fields.assignee.emailAddress
            issue_data["issue_assignee_name"] = issue.fields.assignee.displayName
        else:
            issue_data["issue_assignee_name"] = '未分配'
        if issue.fields.reporter:
            issue_data["issue_reporter"] = issue.fields.reporter.key
            issue_data["issue_reporter_email"] = issue.fields.reporter.emailAddress
            issue_data["issue_reporter_name"] = issue.fields.reporter.displayName
        if issue.fields.creator:
            issue_data["issue_creator"] = issue.fields.creator.key
            issue_data["issue_creator_email"] = issue.fields.creator.emailAddress
        if issue.fields.components:
            issue_data["issue_components_name"] = issue.fields.components[0].name
            issue_data["issue_components_id"] = issue.fields.components[0].id
        if hasattr(issue.fields, 'customfield_11612') and issue.fields.customfield_11612:
            issue_data["issue_remote"] = issue.fields.customfield_11612.value
        if hasattr(issue.fields, 'customfield_11503') and issue.fields.customfield_11503:
            issue_data["issue_pmd_no"] = issue.fields.customfield_11503
        if hasattr(issue.fields, 'customfield_11701'):
            if issue.fields.customfield_11701:
                issue_data["issue_product"] = issue.fields.customfield_11701.value
            else:
                issue_data["issue_product"] = '未知'
        if hasattr(issue.fields, 'customfield_10906') and issue.fields.customfield_10906:
            issue_data["issue_core_version"] = issue.fields.customfield_10906
        if hasattr(issue.fields, 'customfield_10601') and issue.fields.customfield_10601:
            issue_data["issue_commit_yes"] = issue.fields.customfield_10601[0].value
        # biz
        issue_data["issue_solution"] = []
        if hasattr(issue.fields, 'customfield_11878') and issue.fields.customfield_11878:
            issue_data["issue_solution"] = [i.value for i in issue.fields.customfield_11878]
        # core
        if hasattr(issue.fields, 'customfield_12274') and issue.fields.customfield_12274:
            issue_data["issue_solution"] = [i.value for i in issue.fields.customfield_12274]

        if hasattr(issue.fields, 'customfield_11829') and issue.fields.customfield_11829:
            issue_data["issue_attribute"] = [i.value for i in issue.fields.customfield_11829]
        else:
            issue_data["issue_attribute"] = []
        if hasattr(issue.fields, 'customfield_11613') and issue.fields.customfield_11613:
            issue_data["issue_cause"] = [i.value for i in issue.fields.customfield_11613]
        else:
            issue_data["issue_cause"] = []
        if hasattr(issue.fields, 'customfield_12272') and issue.fields.customfield_12272:
            issue_data['issue_biz_group'] = issue.fields.customfield_12272.value
            if hasattr(issue.fields.customfield_12272, 'child') and issue.fields.customfield_12272.child:
                issue_data['issue_biz_project'] = issue.fields.customfield_12272.child.value
            else:
                issue_data['issue_biz_project'] = '未知'
        else:
            issue_data['issue_biz_group'] = '未知'
            issue_data['issue_biz_project'] = '未知'

        if hasattr(issue.fields, 'customfield_12273') and issue.fields.customfield_12273:
            issue_data['issue_core_group'] = issue.fields.customfield_12273.value
            if hasattr(issue.fields.customfield_12273, 'child') and issue.fields.customfield_12273.child:
                issue_data['issue_core_project'] = issue.fields.customfield_12273.child.value
            else:
                issue_data['issue_core_project'] = '未知'
        else:
            issue_data['issue_core_group'] = '未知'
            issue_data['issue_core_project'] = '未知'
        # 获取issue所有评论
        issue_c = ja.issue(issue.key)
        data2 = []
        for c in issue_c.fields.comment.comments:
            t = dict()
            t['comments_id'] = c.id
            t['comments'] = c.body
            t['gong_dan_issue_id'] = issue.id
            data2.append(t)
            JiraGongDanComment.update(**t)

        issue_data["issue_type_id"] = issue.fields.issuetype.id
        issue_data["issue_type_name"] = issue.fields.issuetype.name
        issue_data["issue_project_key"] = issue.fields.project.key
        issue_data["issue_summary"] = issue.fields.summary
        issue_data["issue_description"] = issue.fields.description
        issue_data["issue_status"] = issue.fields.status.name
        issue_data["issue_created"] = issue.fields.created
        issue_data["issue_updated"] = issue.fields.updated
        issue_data["issue_priority"] = issue.fields.priority.name
        if issue.fields.fixVersions:
            issue_data["issue_fixVersions"] = issue.fields.fixVersions[0].name
        # print('self', issue_data)
        import datetime
        from dateutil.parser import parse

        issue_create = datetime.datetime.strftime(
            parse(issue.fields.created), "%Y-%m-%d %H:%M:%S"
        )
        issue_created = datetime.datetime.strptime(issue_create, "%Y-%m-%d %H:%M:%S")

        now = datetime.datetime.now()
        now_time = datetime.datetime.strftime(now, "%Y-%m-%d %H:%M:%S")
        done_time = datetime.datetime.strptime(now_time, "%Y-%m-%d %H:%M:%S")

        # 添加change status
        for history in issue.changelog.histories:
            print("Process issue changelog status...")
            # print(history.created)
            for item in history.items:
                # print(item)
                status_dict = {}
                if item.field == "status":
                    if item.field == "status":
                        if item.toString == "完成" or item.toString == "Done":
                            done_time_1 = datetime.datetime.strftime(
                                parse(history.created), "%Y-%m-%d %H:%M:%S"
                            )
                            done_time = datetime.datetime.strptime(
                                done_time_1, "%Y-%m-%d %H:%M:%S"
                            )
                    status_dict["jira_gongdan_id"] = jira_gongdan_id
                    status_dict["filter_id"] = filter_id
                    status_dict["issue_key"] = issue.key
                    status_dict["issue_id"] = issue.id
                    status_dict["change_author"] = history.author.key
                    status_dict["change_created"] = history.created
                    status_dict["change_to_status"] = item.toString
                    status_dict["change_from_status"] = item.fromString
                    jich = JiraGongdanIssueChangeHistory.query.filter(
                        and_(
                            JiraGongdanIssueChangeHistory.jira_gongdan_id
                            == jira_gongdan_id,
                            JiraGongdanIssueChangeHistory.issue_id == issue.id,
                            JiraGongdanIssueChangeHistory.change_from_status
                            == item.fromString,
                            JiraGongdanIssueChangeHistory.change_to_status
                            == item.toString,
                            JiraGongdanIssueChangeHistory.change_created
                            == history.created,
                            JiraGongdanIssueChangeHistory.filter_id == filter_id,
                        )
                    ).first()
                    if jich:
                        jich.update(**status_dict)
                    else:
                        JiraGongdanIssueChangeHistory.add(**status_dict)

        issue_duration = (done_time - issue_created).seconds
        issue_data["issue_duration"] = issue_duration
        jic = JiraGongdanIssue.query.filter(
            and_(
                JiraGongdanIssue.jira_gongdan_id == jira_gongdan_id,
                JiraGongdanIssue.issue_id == issue_data["issue_id"],
                JiraGongdanIssue.filter_id == filter_id,
            )
        ).first()
        if jic:
            print("jic exists")
            jic.update(**issue_data)
        else:
            print("jic not exists")
            JiraGongdanIssue.add(**issue_data)


def update_gongdan_issue_duration(jira_gongdan_id, filter_id):
    # status_dict={}
    # status_dict["status_duration"] = '0'
    all = JiraGongdanIssueChangeHistory.query.filter(
        and_(
            JiraGongdanIssueChangeHistory.jira_gongdan_id
            == jira_gongdan_id,
            JiraGongdanIssueChangeHistory.filter_id == filter_id,
        )
    ).order_by(desc(JiraGongdanIssueChangeHistory.change_created)).all()
    # print('111111',all)
    for i in all:
        # print(i)
        issue_id = i.issue_id
        change_from_status = i.change_from_status
        change_created = i.change_created
        print(issue_id, change_from_status, change_created, jira_gongdan_id, filter_id)
        jich_before = db.session.query(JiraGongdanIssueChangeHistory.change_created).filter(
            and_(
                JiraGongdanIssueChangeHistory.jira_gongdan_id == jira_gongdan_id,
                JiraGongdanIssueChangeHistory.filter_id == filter_id,
                JiraGongdanIssueChangeHistory.issue_id == issue_id,
                JiraGongdanIssueChangeHistory.change_to_status == change_from_status,
                JiraGongdanIssueChangeHistory.change_created < change_created
            )
        ).order_by(desc(JiraGongdanIssueChangeHistory.change_created)).first()
        print('9999', jich_before)
        status_dict = {}
        status_dict["jira_gongdan_id"] = jira_gongdan_id
        status_dict["filter_id"] = filter_id
        status_dict["issue_key"] = i.issue_key
        status_dict["issue_id"] = i.issue_id
        status_dict["change_author"] = i.change_author
        status_dict["change_created"] = i.change_created
        status_dict["change_to_status"] = i.change_to_status
        status_dict["change_from_status"] = i.change_from_status
        status_dict["status_duration"] = '0'
        if jich_before != None:
            t = [j for j in jich_before]
            status_dict["status_duration"] = (change_created - t[0]).total_seconds()
            print(status_dict["status_duration"])
            # i["status_duration"] = t[0]
            print('2123', t[0])
            i.update(**status_dict)
        else:
            jich_before2 = db.session.query(JiraGongdanIssue.issue_created).filter(
                JiraGongdanIssue.issue_id == issue_id

            ).first()
            t2 = [j for j in jich_before2]
            status_dict["status_duration"] = (change_created - t2[0]).total_seconds()
            print(status_dict["status_duration"])

            i.update(**status_dict)

        # i["status_duration"] = '0'
        # print('2123',i)
        # jich_before = JiraGongdanIssueChangeHistory.query(
        #     JiraGongdanIssueChangeHistory.change_created).filter(
        #     and_(
        #         JiraGongdanIssueChangeHistory.jira_gongdan_id
        #         == jira_gongdan_id,
        #         JiraGongdanIssueChangeHistory.issue_id == issue_id,
        #         JiraGongdanIssueChangeHistory.change_to_status
        #         == change_from_status,
        #         JiraGongdanIssueChangeHistory.change_created
        #         < change_created,
        #         JiraGongdanIssueChangeHistory.filter_id == filter_id,
        #     )
        # ).order_by(desc(JiraGongdanIssueChangeHistory.change_created)).all()
        # for j in jich_before:
        #     print(j,j[0])

        # if jich_before:
        #     print('111111',jich_before)
        # i["status_duration"]=(i.change_created - jich_before[0]).total_seconds()


if __name__ == "__main__":
    get_jira_gongdan_issue_change_cycle()
