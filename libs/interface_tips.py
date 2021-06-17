from enum import Enum


class InterfaceTips(Enum):
    # [10000: 10100)
    INVALID_REQUEST = (400, 10000, "不合法的请求")
    INVALID_TOKEN = (401, 10001, "无效的token")
    EXPIRED_TOKEN = (401, 10002, "token失效，请重新登陆")
    MISSING_TOKEN = (401, 10003, "token 缺失")
    REVOKED_TOKEN = (401, 10004, "token 已被收回")
    INSUFFICIENT_PERMISSION = (403, 10005, "权限不足")

    # [10100: 10200)
    LOGIN_ERROR = (422, 10100, "邮箱或者密码错误")
    FUNCTION_ERROR = (422, 10101, "找不到该项目")
    USER_ERROR = (422, 10102, "找不到该用户")
    SERVE_EXIST_ERROR = (422, 10103, "已存在该机器")
    SERVE_LOGIN_ERROR = (422, 10104, "服务器账号或者密码错误")
    PROJECT_EXIST_ERROR = (422, 10105, "项目已存在")
    TIME_CONFLICT = (422, 10106, "时间冲突")
    NO_NEW_TASK = (422, 10107, "没有最新任务")
    TASK_DEPLOYING = (422, 10108, "有任务正在部署")
    EMAIL_EXIST_ERROR = (422, 10109, "已存在该邮箱用户")

    # [10200: 10300)
    SERVER_ERROR = (500, 10200, "去找客服小姐姐吐槽技术小哥哥")

    # gitlab相关
    GITLAB_PROJECT_ALREADY_EXIST = (422, 20000, "gitlab项目和分支已存在")
    GITLAB_PROJECT_NOT_EXIST = (422, 20001, "gitlab项目不存在")
    GITLAB_PROJECT_URL_NOT_EXIST = (422, 20002, "gitlab url获取失败")
    GITLAB_PROJECT_BRANCHES_NOT_EXIST = (422, 20003, "gitlab 分支获取失败")
    GITLAB_PROJECT_URL_WRONG = (422, 20004, "git地址和git项目ID不对应")
    # jenkins相关
    JENKINS_JOB_NOT_EXIST = (422, 20010, "Jenkins job不存在")
    # 性能测试结果相关
    PERF_RECORD_RESULT_NOT_EXIST = (422, 20020, "该记录不存在性能测试结果")

    # elk log相关
    LOG_KIBANA_INDEX_IS_EMPTY = (422, 20030, "kibana索引为空")
    LOG_KIBANA_DASHBOARD_IS_EMPTY = (422, 20031, "kibana dashboard为空")

    # elk log client相关
    LOG_CLIENT_WRONG_STATUS_CODE = (422, 20040, "status错误，请检查！")
    LOG_CLIENT_CONNECT_FAIL = (422, 20041, "服务器无法连接！")
    LOG_DASHBOARD_PROJECT_ALREADY_EXISTS = (422, 20042, "项目版本已存在！")

    # 性能测试Jenkins job相关
    JENKINS_TASK_ALREADY_EXISTS = (422, 20050, "该项目测试任务已存在！")
    JENKINS_TASK_PARAM_ERROR = (422, 20051, "参数不全请检查！")

    # Jira相关
    JIRA_PROJECT_NOT_EXIST = (422, 20060, "Jira项目不存在！")
    JIRA_FILTER_NOT_EXIST = (422, 20061, "Jira 过滤ID不存在！")
    JIRA_BUG_FILTER_NOT_EXIST = (422, 20062, "Jira Bug Filter不存在！")
    JIRA_CASE_FILTER_NOT_EXIST = (422, 20063, "Jira Case Filter不存在！")
    JIRA_PROJECT_ERROR = (422, 20064, "Jira项目连接失败！")
    JIRA_PROJECT_ALREADY_EXIST = (422, 20065, "Jira项目已存在！")



