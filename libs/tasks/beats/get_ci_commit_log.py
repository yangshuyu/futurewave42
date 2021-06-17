# -*- coding: utf-8 -*-
from ec.ext import celery, db
from libs.ci_util.gitlab_util import GitlabAPI


@celery.task(name="git_ci_commit_log")
def git_ci_commit_log():
    from ec.ci_cd.model import CICommit, CIProject
    ci_projects = db.session.query(CIProject.gitlab_project_id, CIProject.branch_name).all()
    # print(len(ci_projects))
    g = GitlabAPI()
    commit_list = []
    commit_num = 0
    for i in ci_projects:
        project_id = i[0]
        branch_name = i[1]
        project = g.gl.projects.get(project_id)
        commits = project.commits.list(ref_name=branch_name, all=True)
        commits_id_list = []
        for c in commits:
            commits_id_list.append(c.id)
            commit_num += 1
        for id in commits_id_list:
            t = {'branch_name': branch_name, 'gitlab_id': project_id, 'commit_id': id}
            commit_list.append(t)
    for c in commit_list:
        # print(c)
        # print(CICommit.add(**c))
        CICommit.add(**c)

