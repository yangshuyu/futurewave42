# -*- coding: utf-8 -*-
# Created by Duanwei on 2020/7/14

import json
import datetime
import dateutil.parser
from ec.ext import db
import requests
from sqlalchemy import or_, and_
from ec.ext import celery
from ec.ci_cd.model import GitlabCICommit
from ec.department_opti.model import EcStaff


@celery.task(name="get_gitlab_commit_data")
def get_gitlab_commit_data():
    UTC_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"
    url = "https://git-pd.megvii-inc.com/"
    header = {"private-token": "JiAZTRsvgLpssxP4b4Tt"}
    # 获取所有需要拉取的gitlab staff
    all_gitlab_staff = (
        EcStaff.query.filter(and_(EcStaff.gitlab_user, EcStaff.empStatus == "Norm"))
        .with_entities(EcStaff.staff_name_2)
        .all()
    )
    # 获取需要获取数据的部门ID
    dept_id_list = ["S322"]
    # 获取部门所有人员名单
    break_flag = False
    # for dept_id in dept_id_list:
    #     dept_staff = (
    #         EcStaff.query.filter(EcStaff.staff_dept_no == dept_id)
    #         .with_entities(EcStaff.staff_name_2)
    #         .all()
    #     )
    #     print(dept_staff)
    if all_gitlab_staff:
        for staff in all_gitlab_staff:
            # 获取用户最新一条commit日期
            staff = staff[0]
            staff_latest_commit_date = (
                GitlabCICommit.query.filter(GitlabCICommit.author_username == staff)
                .with_entities(GitlabCICommit.commit_date)
                .order_by(GitlabCICommit.commit_date.desc())
                .first()
            )
            print("staff_latest_commit_date: %s" % str(staff_latest_commit_date))
            print(type(staff_latest_commit_date))
            if not staff_latest_commit_date:
                staff_latest_commit_date = datetime.datetime(
                    2000, 1, 1, 14, 56, 50, 231937
                )
                # staff_latest_commit_date = None
            else:
                staff_latest_commit_date = staff_latest_commit_date[0].replace(
                    tzinfo=None
                )
            # print(staff_latest_commit_date)
            # 获取用户信息
            git_user_addr = "%s/api/v4/users?username=%s" % (url, staff)
            res = requests.get(git_user_addr, headers=header).json()
            print(staff, res)
            if res:
                user_id = res[0]["id"]
                print("user_name: %s; user_id: %s" % (staff, user_id))
                page = 1
                # 获取用户所有的代码提交记录
                while page:
                    git_user_push = (
                        "%s/api/v4//users/%d/events?action=pushed&page=%s"
                        % (url, user_id, page)
                    )
                    res_2 = requests.get(git_user_push, headers=header)
                    page = res_2.headers["X-Next-Page"]
                    res_2 = res_2.json()
                    if res_2:
                        for i in res_2:
                            commit_dict = dict()
                            project_id = i['project_id']
                            if 'push_data' in i:
                                commit_to = i['push_data']['commit_to']
                                git_user_commit = "%s/api/v4/projects/%d/repository/commits/%s" % (url, project_id, commit_to)
                                res_3 = requests.get(git_user_commit, headers=header).json()
                                commit_dict['commit_id'] = res_3['id']
                                commit_dict['committed_date'] = datetime.datetime.strptime(res_3["committed_date"], UTC_FORMAT)
                                commit_dict['author_name'] = res_3['author_name']
                                commit_dict['author_email'] = res_3['author_email']
                                commit_dict['gitlab_project_id'] = res_3['project_id']
                                commit_dict['web_url'] = res_3['web_url']
                                commit_dict['web_url'] = res_3['web_url']
                                commit_dict['title'] = res_3['title']
                                if 'stats' in res_3:
                                    commit_dict['additions'] = res_3['status']['additions']
                                    commit_dict['deletions'] = res_3['status']['deletions']
                                    commit_dict['total'] = res_3['status']['total']

                                utc_created_time = datetime.datetime.strptime(
                                    res_3["committed_date"], UTC_FORMAT
                                )
                                utc_created_time_localtime = (
                                    utc_created_time + datetime.timedelta(hours=8)
                                )
                            # print(
                            #     "utc_created_time_localtime: %s"
                            #     % str(utc_created_time_localtime)
                            # )
                            # print(
                            #     "staff_latest_commit_date: %s"
                            #     % str(staff_latest_commit_date)
                            # )
                            # dt = dateutil.parser.parse(utc_created_time_localtime)
                                if (utc_created_time_localtime - staff_latest_commit_date).days > 0:
                                    # dict_data = parse_json_to_dict(i)
                                    GitlabCICommit.add(**commit_dict)
                                else:
                                    break_flag = False
                                    print("if break")
                                    break
                        if break_flag:
                            print("res_2 break")
                            break
                if break_flag:
                    print("while break")
                    break
        # if break_flag:
        #     break


def parse_json_to_dict(json_data):
    d = {}
    d["project_id"] = json_data["project_id"]
    d["action_name"] = json_data["action_name"]
    d["target_id"] = json_data["target_id"]
    d["target_iid"] = json_data["target_iid"]
    d["target_type"] = json_data["target_type"]
    d["target_title"] = json_data["target_title"]
    d["author_id"] = json_data["author_id"]
    d["commit_created_at"] = json_data["created_at"]
    d["author_username"] = json_data["author_username"]
    if "author" in json_data:
        d["author_name"] = json_data["author"]["name"]
        d["author_state"] = json_data["author"]["state"]
        d["author_web_url"] = json_data["author"]["web_url"]
    if "push_data" in json_data:
        d["push_data_commit_count"] = json_data["push_data"]["commit_count"]
        d["push_data_action"] = json_data["push_data"]["action"]
        d["push_data_ref_type"] = json_data["push_data"]["ref_type"]
        d["push_data_commit_from"] = json_data["push_data"]["commit_from"]
        d["push_data_commit_to"] = json_data["push_data"]["commit_to"]
        d["push_data_ref"] = json_data["push_data"]["ref"]
        d["push_data_commit_title"] = json_data["push_data"]["commit_title"]

    return d
