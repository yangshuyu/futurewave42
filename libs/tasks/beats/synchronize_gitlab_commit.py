import datetime

import arrow
import requests

from flask_mail import Message
from sqlalchemy import and_

from config import load_config
from ec.account.model import User
from ec.ext import mail, db, celery
from ec.gitlab_measure.model import GitlabCommit


def get_gitlab_users():
    url = load_config().GITLAB_URL + '/users?per_page=100'
    res = requests.get(url, headers={'private-token': load_config().GITLAB_TOKEN})
    pages = int(res.headers.get('X-Total-Pages', 1))
    users = res.json()
    if pages > 1:
        for page in range(2, pages + 1):
            url = load_config().GITLAB_URL + '/users?per_page=100&page={}'. \
                format(page)
            res = requests.get(url, headers={'private-token': load_config().GITLAB_TOKEN})
            if res.status_code == 200:
                users += res.json()

    user_data = {}
    for user in users:
        if user['name'] in ['yanglongfei', 'yang longfei']:
            print(user)
        if user['username'] in ['yanglongfei', 'yang longfei']:
            print(user)
        user_data[user['name']] = [user['name'], user['username']]
        user_data[user['username']] = [user['name'], user['username']]

    return user_data


@celery.task(name='synchronize_gitlab_commit')
def synchronize_gitlab_commit():
    from ec.gitlab.model import GitBranch, GitProjectModule
    # gpms = GitProjectModule.query.filter(GitProjectModule.group_id == '62102208-3b07-4339-89bd-f602c8b01774').all()
    # gpms_ids = [gpm.id for gpm in gpms]

    # git_branchs = GitBranch.query.filter(GitBranch.git_branch != '').\
    #     filter(GitBranch.module_id.in_(gpms_ids)).\
    #     all()
    git_branchs = GitBranch.query.filter(GitBranch.git_branch != ''). \
        all()

    user_data = get_gitlab_users()
    count = 0
    # commits_count = 0
    for git_branch in git_branchs:
        count += 1
        print(len(git_branchs), count)
        git_module = GitProjectModule.query.filter(GitProjectModule.id == git_branch.module_id).first()

        url = load_config().GITLAB_URL + '/projects/{}/repository/commits?per_page=100&ref_name={}'. \
            format(git_module.gitlab_project_id, git_branch.git_branch)
        res = requests.get(url, headers={'private-token': load_config().GITLAB_TOKEN})

        if res.status_code != 200:
            continue

        commits = res.json()
        pages = int(res.headers.get('X-Total-Pages', 1))
        if pages > 1:
            for page in range(2, pages + 1):
                url = load_config().GITLAB_URL + '/projects/{}/repository/commits?per_page=100&page={}&ref_name={}'. \
                    format(git_module.gitlab_project_id, page, git_branch.git_branch)
                res = requests.get(url, headers={'private-token': load_config().GITLAB_TOKEN})
                if res.status_code == 200:
                    commits += res.json()

        # commits_count += len(commits)
        # print('commits_count:', commits_count)

        commit_count = 0

        for commit in commits:
            commit_count += 1

            print('commit_count', len(commits), commit_count)
            #
            # if commit.get('id') == '820f3995d89ea3a1acf40729ade398f9dba531c3':
            #     print(commit)
            #     user = User.query.filter(User.email == commit.get('committer_email')).first()
            #     print(commit.get('committer_name'))
            #     print(user)

            commit_id = commit.get('id')
            old_gitlab_commit = GitlabCommit.query.filter(and_(
                GitlabCommit.gitlab_project_id == git_module.gitlab_project_id,
                GitlabCommit.branch == git_branch.git_branch,
                GitlabCommit.commit_id == commit_id
            )).first()

            if old_gitlab_commit:
                continue
            email = commit.get('committer_email').replace('MEGVII-INC', 'megvii')
            user = User.query.filter(User.email == email).first()
            if not user:
                user_data_info = user_data.get(commit.get('committer_name').replace(' ', ''))

                if not user_data_info:
                    user_data_info = user_data.get(commit.get('author_name').replace(' ', ''))

                if not user_data_info:
                    print('-------------------------')
                    print(commit)
                    continue
                username = user_data_info[1]
                username_email = '{}@megvii.com'.format(user_data_info[1])

                user = User.get_user_and_add(
                    email=username_email,
                    name=username
                )

            if not user:
                continue

            print('--------------------------------')
            print(commit.get('committer_email'))

            gitlab_commit = GitlabCommit(
                user_id=user.id,
                gitlab_project_id=git_module.gitlab_project_id,
                branch=git_branch.git_branch,
                message=commit.get('message'),
                commit_id=commit_id,
                commit_at=commit.get('committed_date'),
            )

            if 'Merge branch' in commit.get('message'):
                gitlab_commit.type = 1
            stats = GitlabCommit.get_stats_by_commit(gitlab_commit)
            gitlab_commit.additions = stats.get('additions', 0)
            gitlab_commit.deletions = stats.get('deletions', 0)
            db.session.add(gitlab_commit)

            try:
                db.session.commit()
            except Exception as e:
                print(e)
