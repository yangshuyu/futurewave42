# -*- coding: utf-8 -*-
# Created by Duanwei on 2019/12/18
from ec.ext import celery
from libs.ci_util.gitlab_util import GitlabAPI


@celery.task
def commit_log(*projectbranchData):
    from ec.ci_cd.model import CICommit
    g = GitlabAPI()
    commit_list = []
    commit_num = 0
    import datetime

    begin_time = datetime.date(2020, 7, 1)
    end_time = datetime.date(2020, 10, 1)
    for i in projectbranchData:
        project_id = i["project_id"]
        branch_name = i["branch_name"]
        project = g.gl.projects.get(project_id)
        commits = project.commits.list(ref_name=branch_name, all=True)
        commits_id_list = []
        for c in commits:
            a = c.committed_date
            date_str = a[:10]
            date = datetime.date(*map(int, date_str.split('-')))
            if date > begin_time and date < end_time:
                commits_id_list.append(c.id)
                commit_num += 1
        i['commits_id_list'] = commits_id_list
        commit_list.append(i)
    print(commit_list)
    print(commit_num)

    for c in commit_list:
        for i in c["commits_id_list"]:
            kwargs = {'branch_name': c["branch_name"], 'gitlab_id': c['project_id'], 'commit_id': i}
            print(CICommit.add(**kwargs))

if __name__ == "__main__":
    projectbranchData= [{'branch_name': 'dev-2.0', 'project_id': '7189'}, {'branch_name': 'release-v4.0', 'project_id': '3793'},
         {'branch_name': 'release-v1.1', 'project_id': '7738'}, {'branch_name': 'release-v2.0', 'project_id': '8266'}]
    commit_log(*projectbranchData)
