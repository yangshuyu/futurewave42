# -*- coding: utf-8 -*-
# Created by Duanwei on 2020/3/10
import requests
import json

from ec.ext import celery
from ec.perftest.model import (
    JenkinsJobTask,
    JenkinsJobTaskRecord,
    JenkinsServer,
    JenkinsJobTaskRecordResult,
)
from libs.ci_util.jenkins_util import JenkinsUtil


@celery.task(name="get_perf_job_infos")
def get_perf_job_infos():
    # 获取task表中的记录，server_id, job_name
    perf_task = JenkinsJobTask.query.with_entities(
        JenkinsJobTask.id, JenkinsJobTask.jenkins_server_id, JenkinsJobTask.job_name
    )
    all_record = perf_task.all()
    for record in all_record:
        task_id = record[0]
        jenkins_server_id = record[1]
        job_name = record[2]
        # 根据server_id获取Jenkins实例
        jenkins_instance = get_jenkins_instance(jenkins_server_id)
        # 获取job详情
        job_builds = jenkins_instance.get_build_list(job_name)
        # 获取job数据库中最新ID
        latest_job_record = (
            JenkinsJobTaskRecord.query.filter(JenkinsJobTaskRecord.task_id == task_id)
            .order_by(JenkinsJobTaskRecord.build_time.desc())
            .first()
        )
        if not latest_job_record:
            latest_job_record_id = 0
        else:
            latest_job_record_id = latest_job_record.build_num
        print("latest_job_record_id is : %s" % str(latest_job_record_id))
        if job_builds:
            for b in job_builds:
                # 获取job记录详情
                build_num = int(b["number"])
                if build_num > int(latest_job_record_id):
                    build_info = jenkins_instance.attr_to_dict(job_name, build_num)
                    build_info["task_id"] = task_id
                    build_time = build_info["build_time"]
                    print(build_info)
                    # 将记录详情写入taskrecord表
                    new_record = JenkinsJobTaskRecord.add(**build_info)
                    new_record_id = new_record.id
                    print("new record id is %s " % str(new_record_id))
                    # 获取记录输出的console log中的结果URL
                    print("jobname: %s, build_num: %s" % (job_name, build_num))
                    result_url, all_url = jenkins_instance.get_job_result_url(
                        job_name, build_num
                    )
                    if all_url:
                        statistics_url = all_url + "/statistics.json"
                        print("statistics_url: %s " % statistics_url)
                        result_list = parse_json(statistics_url)
                        insert_into_record_result(
                            new_record_id, result_url, result_list, build_time
                        )
                else:
                    print("已经读取到最新job 记录")
                    break


def get_jenkins_instance(jenkins_server_id):
    js = JenkinsServer.find_by_id(jenkins_server_id)
    ip, port, username, password = js.ip, js.port, js.username, js.password
    jenkins_instance = JenkinsUtil(ip, port, username, password)
    return jenkins_instance


def parse_json(url):
    result_list = []
    total_login_key = ["Total", "login", "Login", "登录", "用户登录-6.1", "用户登录"]
    try:
        json_data = get_json_statistics(url)
        if json_data:
            jd = json.loads(json_data)
            for k, v in jd.items():
                if k not in total_login_key:
                    result_list.append(v)
        else:
            return result_list
    except Exception as e:
        print("解析json出问题：%s" % str(e))
    return result_list


def get_json_statistics(url):
    USERNAME = "admin"
    PASSWORD = "sngdevqa"
    USER_AGENT = (
        "Mozilla/5.0 (X11; Linux i686) AppleWebKit/537.17 (KHTML, like Gecko) Chrome/24.0.1312.27 "
        "Safari/537.17 "
    )
    CERT_FILE = False

    authed_session = requests.Session()
    authed_session.auth = (USERNAME, PASSWORD)
    authed_session.verify = CERT_FILE
    authed_session.headers.update({"User-Agent": USER_AGENT})
    try:
        response = authed_session.get(url, timeout=60)

        if response.status_code == 200:
            return response.content.decode('utf-8')
        else:
            return None
    except Exception as e:
        print("get json data出问题，原因：%s" % str(e))
        return None


def insert_into_record_result(record_id, result_url, result_list, build_time):
    try:
        if result_list:
            for result in result_list:
                data = {}
                data["result_url"] = result_url
                data["record_id"] = record_id
                data["result_state"] = 1
                data["build_time"] = build_time
                data["result_title"] = result["transaction"]
                data["samples"] = result["sampleCount"]
                data["response_time_avg"] = round(result["meanResTime"], 2)
                data["response_time_min"] = round(result["minResTime"], 2)
                data["response_time_max"] = round(result["maxResTime"], 2)
                data["response_time_90"] = round(result["pct1ResTime"], 2)
                data["response_time_95"] = round(result["pct2ResTime"], 2)
                data["response_time_99"] = round(result["pct3ResTime"], 2)
                data["throughput"] = round(result["throughput"], 2)
                JenkinsJobTaskRecordResult.add(**data)
    except Exception as e:
        print("写性能测试数据失败，原因：%s" % str(e))


if __name__ == "__main__":
    pass
    # url = "http://10.199.0.52:8000/perf/Lingtan_1.2/testvss-people/20200213165741/all/statistics.json"
    # parse_json(url)
