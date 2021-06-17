from __future__ import absolute_import, unicode_literals

import datetime
import json
import os
import time
import re
from ec.ext import celery, mail
from ec.testcenter.models import *
from ec.testcenter.utils.multi_depend import MultiDepend
from requests_toolbelt import MultipartEncoder
from ec.testcenter.utils.runmethod import RunMethod
from ec.testcenter.utils.dynamic_params import DynamicParams
from ec.testcenter.utils.assert_result import AssertResult
from ec.testcenter.utils.html_report import HtmlReport
from ec.testcenter.utils.scenario_report import ScenarioReport
from ec.testcenter.utils.send_email import SendEmail
from libs.logging_log2 import get_logger
from flask_mail import Message as SendMessage

CUR_PATH = os.path.dirname(os.path.realpath(__file__))
FILE_PATH = os.path.join(CUR_PATH, 'uploadfiles')
TEMP_PATH = os.path.join(CUR_PATH, 'temp')

# logger对象
logger = get_logger('test_center')


@celery.task
def celery_exec_single(case_col_obj_id, server, record_obj_id, rely_data_dict, is_create_bug,
                       super_token='59dacfac729esuperadmin427f90bfa98c0a636e0c'):
    """
    # 异步任务执行单个用例集
    :param case_col_obj_id: 用例集合id
    :param server: 服务器地址
    :param record_obj_id: 报告id
    :param rely_data_dict: 依赖数据字典
    :param is_create_bug: 是否创建bug开关
    :return:
    """
    # 变量字典
    rely_data_dict = dict()
    # 执行函数
    run_single_case_col(case_col_obj_id, server, record_obj_id, rely_data_dict, is_create_bug, super_token)


@celery.task
def celery_exec_multi(case_col_obj_id_list, scene_name, is_create_bug, server,
                      super_token='59dacfac729esuperadmin427f90bfa98c0a636e0c', image_id=''):
    """
    # 异步任务执行多个用例集
    :param case_col_obj_id_list: 用例集合id列表
    :param scene_name: 场景测试名称
    :param server: 服务器地址
    :param is_create_bug: 是否创建bug开关
    :param super_token: 服务器超级token
    :return:
    """
    run_single_scenario(case_col_obj_id_list, scene_name, is_create_bug, server, super_token, image_id)


@celery.task
def run_api_scenario_tasks(**kwargs):
    """
    执行接口+场景测试
    :param kwargs:
    :return:
    """
    code = 99
    case_col_task_id = kwargs.get('caseColTaskId')
    scenario_task_id = kwargs.get('scenarioTaskId')
    image_id = kwargs.get('imageId')
    # 执行接口任务
    if case_col_task_id:
        data, code, msg = run_api_task(caseColTaskId=case_col_task_id, imageId=image_id)
    else:
        code = 1
    # 如果接口执行成功或者忽略并且scenario_task_id存在，那么执行场景测试
    if code <= 1 and scenario_task_id:
        run_scenario_task(scenarioTaskId=scenario_task_id, imageId=image_id)


def run_api_task(**kwargs):
    """
    执行接口任务测试
    :param kwargs:
    :return:
    """
    code = 0
    msg = '用例集合未执行'
    data = dict()
    case_col_task_id = kwargs.get('caseColTaskId')
    image_id = kwargs.get('imageId')
    case_col_task_obj = CasesColTask.find_one(id=case_col_task_id)
    if case_col_task_obj:
        case_col_id = str(case_col_task_obj.case_col_ref.id)
        server = case_col_task_obj.hostName
        is_create_bug = case_col_task_obj.isCreateBug
        super_token = '59dacfac729esuperadmin427f90bfa98c0a636e0c'
        try:
            case_col_obj = CasesCollection.objects.get(id=case_col_id)

            if case_col_obj.cases:
                # 获取用户变量字典
                var_dict = dict()
                pro_obj = case_col_obj.pro_ref
                var_dict.update(**(get_public_var_dict(pro_obj)))
                # 创建结果对象
                record_obj = ExecuteRecord.add()
                data['recordId'] = str(record_obj.id)
                record_obj.isAutoRun = 1
                record_obj.imagesId = image_id
                # 记录报告执行人
                username = 'admin'  # get_token_user(request)
                user_obj = User.objects.filter(username=username).first()
                record_obj.user_ref = user_obj
                record_obj.case_col_ref = case_col_obj
                record_obj.caseColName = case_col_obj.caseColName
                # 记录时间
                record_obj.runDateTime = datetime.datetime.now()
                if case_col_obj.pro_ref:
                    record_obj.product = case_col_obj.pro_ref.product
                    record_obj.version = case_col_obj.pro_ref.version
                    record_obj.pro_ref = case_col_obj.pro_ref
                record_obj.hostName = server
                record_obj.status = '进行中'
                record_obj.save()
                # 执行函数
                run_single_case_col(str(case_col_obj.id), server, str(record_obj.id), var_dict, is_create_bug,
                                    super_token)

                # 判断结果
                if record_obj.reload().isPass:
                    msg = '执行成功'
                else:
                    code = 4
                    msg = '执行完成，结论为失败'
            else:
                code = 1
                msg = '没有要执行的用例，请先添加用例再执行！'
        except Exception as e:
            logger.info(str(e))
            code = 2
            msg = '错误，执行用例集合失败：' + str(e)
    else:
        code = 3
        msg = '找不到相关用例集任务'

    return data, code, msg


def run_scenario_task(**kwargs):
    """
    执行场景任务测试
    :param kwargs:
    :return:
    """
    code = 0
    msg = '场景测试未执行'
    data = dict()
    scenario_task_id = kwargs.get('scenarioTaskId')
    image_id = kwargs.get('imageId')
    scenario_task_obj = ScenarioTask.find_one(id=scenario_task_id)
    if scenario_task_obj:
        case_col_obj_id_list = scenario_task_obj.scenario_ref.caseCols
        server = scenario_task_obj.hostName
        is_create_bug = scenario_task_obj.isCreateBug
        scene_name = scenario_task_obj.scenario_ref.sceneName
        super_token = '59dacfac729esuperadmin427f90bfa98c0a636e0c'
        # 数据依赖字典
        rely_data_dict = dict()
        rely_data_dict.update(**(get_public_var_dict(scenario_task_obj.pro_ref)))
        # 执行主程序
        scenario_record_obj = run_single_scenario(case_col_obj_id_list, scene_name, rely_data_dict, is_create_bug,
                                                  server, super_token, image_id)
        if scenario_record_obj:
            scenario_record_obj.update_item(
                scenarioTaskName=scenario_task_obj.scenarioTaskName,
                scenario_ref=scenario_task_obj.scenario_ref,
                scenario_task_ref=scenario_task_obj
            )

        # 判断结果
        if scenario_record_obj.reload().isPass:
            msg = '场景测试执行成功'
        else:
            code = 4
            msg = '场景测试执行失败'
    else:
        code = 1
        msg = '找不到相关的场景'

    return data, code, msg


def run_single_case_col(case_col_obj_id, server, record_obj_id, rely_data_dict, is_create_bug, super_token):
    """
    # 执行单个用例集函数
    :param case_col_obj_id: 用例集合id
    :param server: 服务器地址
    :param record_obj_id: 报告id
    :param rely_data_dict: 依赖数据字典
    :param is_create_bug: 是否创建bug开关
    :return:
    """
    # 加入随机变量
    dynamic_vars_obj = DynamicParams()
    rely_data_dict.update(**(dynamic_vars_obj.get_time_dict(datetime.datetime.now())))

    # 执行主程序
    exec_col_main(case_col_obj_id, server, record_obj_id, rely_data_dict, is_create_bug, super_token)
    # 生成report result
    report_result = ExecuteRecord.generate_report_result(record_obj_id)
    try:
        # 生成html report
        html_report_obj = HtmlReport(**report_result)
        generate_report = html_report_obj.run()
        # 发送邮件
        pro_obj = ExecuteRecord.find_one(id=record_obj_id).pro_ref
        if pro_obj:
            send_mail_list, email_code, email_msg = Product.get_email_list(pro_obj.ec_id)
        else:
            send_mail_list = []
        # send_mail_obj = SendEmail()
        # send_mail_obj.send_main(html_report_obj.title, generate_report, send_mail_list)
        send_mail_obj = SendMessage(html_report_obj.title, recipients=send_mail_list)
        send_mail_obj.html = generate_report
        mail.send(send_mail_obj)
    except Exception as e:
        logger.info('接口测试发邮件失败：' + str(e))


def run_single_scenario(case_col_obj_id_list, scene_name, rely_data_dict, is_create_bug, server, super_token, image_id):
    """
    # 执行场景测试
    :param case_col_obj_id_list: 用例集合id列表
    :param scene_name: 场景测试名称
    :param rely_data_dict: 公共用户变量字典
    :param server: 服务器地址
    :param is_create_bug: 是否创建bug开关
    :param super_token: 服务器超级token
    :return:
    """
    scenario_obj = ScenarioRecord.add(sceneName=scene_name)
    # 总case数量
    case_total = 0
    # 成功数量
    case_succ = 0
    # 失败数量
    case_fail = 0
    # 忽略执行数量
    case_ignored = 0
    # 不同优先级case数量
    priority_high_fail = 0
    priority_medium_total = 0
    priority_medium_success = 0
    # 多个用例集
    start_time = datetime.datetime.now()
    # 加入随机变量
    # dynamic_vars_obj = DynamicParams()
    # rely_data_dict.update(**(dynamic_vars_obj.get_time_dict(datetime.datetime.now())))

    # 产品对象
    pro_obj = None
    for i in case_col_obj_id_list:
        try:
            # 加入随机变量
            dynamic_vars_obj = DynamicParams()
            rely_data_dict.update(**(dynamic_vars_obj.get_time_dict(datetime.datetime.now())))

            case_col_obj = CasesCollection.objects.get(id=i)

            if case_col_obj.cases:
                pro_obj = case_col_obj.pro_ref
                # 创建结果对象
                record_obj = ExecuteRecord().add()
                # isAutoRun=1，记录镜像列表id
                record_obj.isAutoRun = 1
                record_obj.imagesId = image_id
                # 记录报告执行人
                username = 'admin'  # get_token_user(request)
                user_obj = User.objects.filter(username=username).first()
                record_obj.user_ref = user_obj
                record_obj.case_col_ref = case_col_obj
                record_obj.caseColName = case_col_obj.caseColName
                # 记录时间
                record_obj.runDateTime = datetime.datetime.now()
                if case_col_obj.pro_ref:
                    record_obj.product = case_col_obj.pro_ref.product
                    record_obj.version = case_col_obj.pro_ref.version
                    record_obj.pro_ref = case_col_obj.pro_ref
                record_obj.hostName = server
                record_obj.status = '进行中'
                record_obj.save()

                # 执行celery任务
                ret_dict = exec_col_main(i, server, str(record_obj.id), rely_data_dict, is_create_bug, super_token,
                                         scenario_obj)
                case_total += ret_dict['caseTotal']
                case_succ += ret_dict['caseSuccess']
                case_fail += ret_dict['caseFailed']
                case_ignored += ret_dict['caseIgnored']
                priority_high_fail += ret_dict['priorityHighFail']
                priority_medium_total += ret_dict['priorityMediumTotal']
                priority_medium_success += ret_dict['priorityMediumSuccess']
                code = 0
                msg = '已经开始执行接口，请查看报告'
            else:
                code = 1
                msg = '没有要执行的用例，请先添加用例再执行！'
        except:
            code = 2
            msg = '错误，执行用例集合失败'
    end_time = datetime.datetime.now()
    scene_dict = dict()
    scene_dict['pro_ref'] = pro_obj
    scene_dict['caseTotal'] = case_total
    scene_dict['caseSuccess'] = case_succ
    scene_dict['caseFailed'] = case_fail
    scene_dict['caseIgnored'] = case_ignored
    scene_dict['runDateTime'] = start_time
    scene_dict['endDateTime'] = end_time
    scene_dict['duration'] = str(end_time - start_time)
    scene_dict['hostName'] = server
    scene_dict['status'] = '完成'
    scene_dict['isAutoRun'] = 1
    # 总通过率
    if case_total:
        case_rate = float('%.2f' % (case_succ / case_total))
    else:
        case_rate = float(0)
    scene_dict['passRate'] = case_rate
    # 给出是否通过的结论
    if case_rate < 0.60:
        scene_dict['conclusion'] = '失败'
        scene_dict['isPass'] = 0
    else:
        if priority_high_fail:
            scene_dict['conclusion'] = '失败'
            scene_dict['isPass'] = 0
        else:
            if priority_medium_total:
                medium_pass_rate = priority_medium_success / priority_medium_total
                if medium_pass_rate >= 0.80:
                    scene_dict['conclusion'] = '通过'
                    scene_dict['isPass'] = 1
                else:
                    scene_dict['conclusion'] = '失败'
                    scene_dict['isPass'] = 0
            else:
                scene_dict['conclusion'] = '通过'
                scene_dict['isPass'] = 1

    scenario_obj.update_item(**scene_dict)

    # 生成report result
    report_result = ScenarioRecord.generate_report_result(str(scenario_obj.id))
    try:
        # 生成html report
        html_report_obj = ScenarioReport(**report_result)
        generate_report = html_report_obj.run()
        # 发送邮件
        if pro_obj:
            send_mail_list, email_code, email_msg = Product.get_email_list(pro_obj.ec_id)
        else:
            send_mail_list = []
        # send_mail_obj = SendEmail()
        # send_mail_obj.send_main(html_report_obj.title, generate_report, send_mail_list)
        send_mail_obj = SendMessage(html_report_obj.title, recipients=send_mail_list)
        send_mail_obj.html = generate_report
        mail.send(send_mail_obj)
    except Exception as e:
        logger.info('场景测试发邮件失败：' + str(e))

    return scenario_obj


def exec_col_main(case_col_obj_id, server, record_obj_id, rely_data_dict, is_create_bug, super_token,
                  scenario_obj=None):
    """
    # 执行批量用例
    :param case_col_obj_id: 用例集合id
    :param server: 服务器地址
    :param record_obj_id: 报告id
    :param rely_data_dict: 依赖数据字典
    :param is_create_bug: 是否创建bug开关
    :return:
    """
    case_col_obj = CasesCollection.objects.filter(id=case_col_obj_id).first()
    record_obj = ExecuteRecord.objects.filter(id=record_obj_id).first()
    # 产品
    product = case_col_obj.pro_ref.product
    # 总case数量
    case_total = 0
    # 成功数量
    case_succ = 0
    # 失败数量
    case_fail = 0
    # 忽略执行数量
    case_ignored = 0
    # 不同优先级case数量
    priority_high_fail = 0
    priority_medium_total = 0
    priority_medium_success = 0
    # 依赖数据字典
    # rely_data_dict = dict()
    # 开始执行
    for i in case_col_obj.cases:
        # 结果字典
        # case_result_dict = dict()
        case_total += 1
        case_start_time = datetime.datetime.now()
        case_result_dict = exec_single_main(i.get('uuid'), rely_data_dict, server, super_token, product)
        case_stop_time = datetime.datetime.now()
        case_result_dict["spendTime"] = str(case_stop_time - case_start_time)

        # 是否需要开bug
        need_create_bug = False
        # 用例优先级
        case_priority = case_result_dict["priority"]
        if not case_priority:
            case_priority = ''
        if case_priority == 'Medium':
            priority_medium_total += 1
        # 断言
        if case_result_dict["isSuccess"]:
            case_succ += 1
            if case_priority == 'Medium':
                priority_medium_success += 1
        else:
            if case_priority in ['Highest', 'High']:
                priority_high_fail += 1
            if case_result_dict["isIgnored"]:
                case_ignored += 1
            else:
                case_fail += 1
                need_create_bug = True
            logger.info(i.get('caseName') + ' - 执行失败')

        # 创建用例结果对象
        case_result_obj = CaseResult()
        try:
            # 保存更多信息到用例结果对象中
            case_result_obj.record_ref = record_obj
            case_data_to_result(i.get('uuid'), case_result_obj, case_result_dict)
            # 最后保存一下
            case_result_obj.save()
            # 判断是否要开bug
            if is_create_bug and need_create_bug:
                bug_dict = dict()
                bug_dict['recordId'] = record_obj_id
                bug_dict['caseResultId'] = str(case_result_obj.id)
                bug_dict['proId'] = str(case_result_obj.pro_ref.id)
                bug_dict['bugTitle'] = "接口测试：" + case_result_obj.apiName + "失败"
                bug_dict['creator'] = record_obj.user_ref.username
                ApiBugRecord.create_api_bug(**bug_dict)
        except Exception as e:
            logger.info('保存结果失败：' + str(e))
        # 执行完是否需要等待
        if case_result_obj.waitTime:
            time.sleep(case_result_obj.waitTime)

    # 全部执行完统计数目并计算duration
    record_obj.caseTotal = case_total
    record_obj.caseSuccess = case_succ
    record_obj.caseFailed = case_fail
    record_obj.caseIgnored = case_ignored
    if case_total:
        case_rate = float('%.2f' % (case_succ / case_total))
    else:
        case_rate = float(0)
    record_obj.passRate = case_rate
    end_datetime = datetime.datetime.now()
    record_obj.endDateTime = end_datetime
    record_obj.duration = str(end_datetime - record_obj.runDateTime)
    record_obj.status = '完成'
    # 给出是否通过的结论
    if case_rate < 0.60:
        record_obj.conclusion = '失败'
        record_obj.isPass = 0
    else:
        if priority_high_fail:
            record_obj.conclusion = '失败'
            record_obj.isPass = 0
        else:
            if priority_medium_total:
                medium_pass_rate = priority_medium_success / priority_medium_total
                if medium_pass_rate >= 0.80:
                    record_obj.conclusion = '通过'
                    record_obj.isPass = 1
                else:
                    record_obj.conclusion = '失败'
                    record_obj.isPass = 0
            else:
                record_obj.conclusion = '通过'
                record_obj.isPass = 1
    # 如果是场景测试，记录场景外键
    if scenario_obj:
        record_obj.scenario_record_ref = scenario_obj
    record_obj.save()

    # 返回的数据字典
    ret_dict = dict()
    ret_dict['caseTotal'] = case_total
    ret_dict['caseSuccess'] = case_succ
    ret_dict['caseFailed'] = case_fail
    ret_dict['caseIgnored'] = case_ignored
    ret_dict['priorityHighFail'] = priority_high_fail
    ret_dict['priorityMediumTotal'] = priority_medium_total
    ret_dict['priorityMediumSuccess'] = priority_medium_success

    return ret_dict


def exec_single_main(case_uuid, rely_data_dict, server, super_token, product):
    """
    # 根据case uuid执行单个用例
    :param case_id:
    :param server:
    :return:
    """
    # 用例执行结果字典
    result_dict = dict()
    result_dict["code"] = 0
    result_dict["statusCode"] = 0
    result_dict["url"] = None
    result_dict["header"] = None
    result_dict["reqBody"] = None
    result_dict["resBody"] = None
    result_dict["msg"] = ''
    result_dict["isSuccess"] = True
    result_dict["usedDependDict"] = dict()
    result_dict["isIgnored"] = False
    result_dict["nofFoundDepend"] = []
    result_dict["errorAnalysis"] = ''
    result_dict["priority"] = None
    try:
        case_obj = Cases.objects.get(uuid=case_uuid)
        # 读优先级
        result_dict["priority"] = case_obj.priority
        # 读请求body
        case_data = case_obj.reqBody
        # 请求不空时
        if case_data:
            case_data = removeComments(case_data)
            # case_data格式化一下，避免格式特别造成的匹配问题
            try:
                case_data = json.dumps(json.loads(case_data), ensure_ascii=False, indent=2)
            except Exception as e:
                logger.error(str(e))
            # 将依赖数据填入case_data
            case_data, used_depend_dict, depend_code, not_found_depend_list = format_str(case_data, rely_data_dict)
            result_dict["usedDependDict"].update(used_depend_dict)
            result_dict["reqBody"] = case_data
            case_data = json.loads(case_data)
        else:
            case_data = None
            depend_code = 0
            not_found_depend_list = []
            result_dict["reqBody"] = case_data
        # 读url
        url = case_obj.url
        # 将依赖数据填入url
        url, used_depend_dict, depend_code2, not_found_depend_list2 = format_str(url, rely_data_dict)
        result_dict["usedDependDict"].update(used_depend_dict)
        # 如果有数据依赖没找到，直接忽略用例
        if depend_code or depend_code2:
            result_dict["code"] = 3
            result_dict["msg"] = '忽略此用例，因为没有找到依赖数据'
            result_dict["isSuccess"] = False
            result_dict["isIgnored"] = True
            if depend_code:
                result_dict["nofFoundDepend"].append(*not_found_depend_list)
            if depend_code2:
                result_dict["nofFoundDepend"].append(*not_found_depend_list2)
            result_dict["nofFoundDepend"] = list(set(result_dict["nofFoundDepend"]))
            result_dict["errorAnalysis"] = '没有获取数据依赖，因此忽略此用例'
        else:
            # 读请求方法
            method = case_obj.reqMethod
            # 读header
            headerName = case_obj.headerName
            if not headerName:
                headerName = '普通'
            # 读断言列表和断言状态码
            assert_list = case_obj.assertList
            assert_status_code = case_obj.assertStatusCode
            if not assert_status_code:
                assert_status_code = 200
            if isinstance(assert_status_code, str):
                try:
                    assert_status_code = int(assert_status_code)
                except:
                    assert_status_code = 200
            # 读数据依赖
            depend_obj = case_obj.depend_ref
            if depend_obj:
                # 必须转换成标准list类型，否则出问题
                depend_list = depend_obj.to_mongo().to_dict().get('dependList')
            else:
                depend_list = []
            url = server + url
            if not url.startswith('http'):
                url = 'http://' + url
            server_obj = ServerAddr.objects.get(address=server, product=product)
            header = server_obj.header.get(headerName)
            # 自定义header的情况
            if headerName == '自定义':
                header = case_obj.customHeader
            else:
                token_name = server_obj.tokenName
                if token_name in header:
                    # token = server_obj.token
                    header[token_name] = super_token  # token
            # 判断是否有数据依赖
            # if depend_list:
            #     try:
            #         pro_obj = case_obj.pro_ref
            #         depend_list = exec_depend_main(depend_list, pro_obj, server_obj)
            #         multi_obj = MultiDepend()
            #         new_url = multi_obj.run_main(url, case_data, depend_list)
            #         if new_url:
            #             url = new_url
            #     except Exception as e:
            #         logger.info(str(e))
            # 判断是否上传文件
            if headerName == '上传文件':
                file_key = case_obj.fileKey
                file_obj = case_obj.file_ref
                file_name = file_obj.name
                fp = file_obj.data.read()
                multi_obj = file_req_data(file_key, file_name, fp, case_data)
                header['Content-Type'] = multi_obj.content_type
                res, status_code = exec_main(method, url, multi_obj, header)
            else:
                res, status_code = exec_main(method, url, case_data, header)
            # 如果需要提取返回结果的值
            if case_obj.saveResAsParams:
                update_res_params_to_dict(res, case_obj.saveResAsParams, rely_data_dict)
                update_public_var_dict(case_obj.pro_ref, rely_data_dict)
            # 写入字典
            result_dict["resBody"] = res
            result_dict["statusCode"] = status_code
            result_dict["url"] = url
            result_dict["header"] = header
            # result_dict["isIgnored"] = False
            # 断言
            if assert_result(status_code, res, assert_status_code, assert_list):
                result_dict["msg"] = '完成！恭喜，用例执行成功！'
                result_dict["isSuccess"] = True
            else:
                result_dict["code"] = 1
                result_dict["msg"] = '完成！很遗憾，用例执行失败！'
                result_dict["isSuccess"] = False
    except Exception as e:
        logger.info('用例执行过程失败：' + str(e))
        result_dict["resBody"] = None
        result_dict["code"] = 2
        result_dict["msg"] = '警告，执行用例失败：' + str(e)

    return result_dict


def case_data_to_result(case_uuid, case_result_obj, case_result_dict):
    """
    # 用例数据同步到用例结果对象中
    :param case_uuid:
    :param case_result_obj:
    :param case_result_dict:
    :return:
    """
    try:
        # 基本信息入库
        case_obj = Cases.objects.get(uuid=case_uuid)
        case_result_obj.case_ref = case_obj
        case_result_obj.caseName = case_obj.caseName
        case_result_obj.api_ref = case_obj.api_ref
        case_result_obj.pro_ref = case_obj.pro_ref
        case_result_obj.apiName = case_obj.apiName
        case_result_obj.module = case_obj.module
        case_result_obj.url = case_obj.url
        case_result_obj.reqMethod = case_obj.reqMethod
        case_result_obj.reqParams = case_obj.reqParams
        case_result_obj.reqBody = case_obj.reqBody
        case_result_obj.developer = case_obj.developer
        case_result_obj.reqBodyComments = case_obj.reqBodyComments
        case_result_obj.waitTime = case_obj.waitTime
        case_result_obj.priority = case_obj.priority
        if case_obj.depend_ref:
            case_result_obj.dependList = case_obj.depend_ref.dependList
        if case_obj.assertList:
            case_result_obj.assertList = case_obj.assertList
        if case_obj.assertStatusCode:
            case_result_obj.assertStatusCode = case_obj.assertStatusCode
        # 执行完结果入库
        case_result_obj.spendTime = case_result_dict.get("spendTime")
        case_result_obj.reqBody = case_result_dict.get("reqBody")
        case_result_obj.resBody = case_result_dict.get("resBody")
        case_result_obj.statusCode = case_result_dict.get("statusCode")
        if case_result_dict.get("url"):
            case_result_obj.url = case_result_dict.get("url")
        case_result_obj.header = case_result_dict.get("header")
        case_result_obj.isSuccess = case_result_dict.get("isSuccess")
        case_result_obj.usedDependDict = case_result_dict.get("usedDependDict")
        case_result_obj.isIgnored = case_result_dict.get("isIgnored")
        case_result_obj.nofFoundDepend = case_result_dict.get("nofFoundDepend")
        case_result_obj.errorAnalysis = case_result_dict.get("errorAnalysis")
        case_result_obj.save()
    except Exception as e:
        logger.info("用例数据同步到用例结果对象失败：" + str(e))


def removeComments(string):
    """
    # 去除注释，string是要去除的字符串
    :param string:
    :return:
    """
    string = re.sub(re.compile("/\*.*?\*/", re.DOTALL), "",
                    string)  # remove all occurance streamed comments (/*COMMENT */) from string
    string = re.sub(re.compile("//((?!\").)*?\n"), "",
                    string)  # remove all occurance singleline comments (//COMMENT\n ) from string
    return string


def format_str(tar_str, var_dict={}):
    """
    # 格式化字符串，支持{{ }},{ }, %()s三种形式
    :param tar_str:
    :param var_dict:
    :return:
    """
    code = 0
    not_found_depend_list = []
    used_depend_dict = dict()
    # 匹配{{}}双括号的情况
    reg = re.compile("\{\{([^\{\}\\n]+?)\}\}")
    match_list = reg.findall(tar_str)
    for i in match_list:
        if i in var_dict:
            try:
                tar_str = tar_str.replace("{{%s}}" % i, str(var_dict[i]))
                used_depend_dict[i] = str(var_dict[i])
            except:
                pass
        else:
            code = 1
            not_found_depend_list.append(i)

    # 匹配{}单括号的情况
    reg = re.compile("\{([^\{\}\\n]+?)\}")
    match_list = reg.findall(tar_str)
    for i in match_list:
        if i in var_dict:
            try:
                tar_str = tar_str.replace("{%s}" % i, str(var_dict[i]))
                used_depend_dict[i] = str(var_dict[i])
            except:
                pass
        else:
            code = 1
            not_found_depend_list.append(i)

    # 匹配%()s的情况
    # try:
    #     tar_str = tar_str % var_dict
    # except:
    #     pass
    reg = re.compile("\%\(([^\(\)\\n]+?)\)s")
    match_list = reg.findall(tar_str)
    for i in match_list:
        if i in var_dict:
            try:
                tar_str = tar_str.replace("%(" + i + ")s", str(var_dict[i]))
                used_depend_dict[i] = str(var_dict[i])
            except:
                pass
        else:
            code = 1
            not_found_depend_list.append(i)

    return tar_str, used_depend_dict, code, not_found_depend_list


def exec_depend_main(depend_list, pro_obj, server_obj):
    """
    # 有数据依赖时执行测试主程序
    :param depend_list:
    :param pro_obj:
    :param server_obj:
    :return:
    """
    server = server_obj.address
    for i in depend_list:
        try:
            case_name = i.get('relyCaseId')
            case_obj = Cases.objects.get(caseName=case_name, pro_ref=pro_obj)
            method = case_obj.reqMethod
            url = case_obj.url
            url = server + url
            if not url.startswith('http'):
                url = 'http://' + url
            data = json.loads(case_obj.reqBody)
            header_name = case_obj.headerName
            header = server_obj.header.get(header_name)
            # 判断是否有数据依赖
            if case_obj.depend_ref:
                depend_obj = case_obj.depend_ref
                # sub_depend_list = depend_obj.dependList
                sub_depend_list = depend_obj.to_mongo().to_dict().get('dependList')
                sub_depend_list = exec_depend_main(sub_depend_list, pro_obj, server_obj)
                multi_obj = MultiDepend()
                new_url = multi_obj.run_main(url, data, sub_depend_list)
                if new_url:
                    url = new_url
            # 判断是否上传文件
            if header_name == '上传文件':
                file_key = case_obj.fileKey
                # 下载文件到临时目录
                if case_obj.file_ref:
                    file_obj = case_obj.file_ref
                    try:
                        fp = file_obj.data.read()
                        file_name = file_obj.name
                        file_path = os.path.join(TEMP_PATH, file_name)
                        with open(file_path, 'wb+') as f:
                            f.write(fp)
                    except Exception as e:
                        logger.info(str(e))
                        file_name = ''
                        pass
                else:
                    file_name = ''
                file_path = os.path.join(TEMP_PATH, file_name)
                if os.path.exists(file_path):
                    fp = open(file_path, 'rb')
                else:
                    fp = None
                multi_obj = file_req_data(file_key, file_name, fp, data)
                header['Content-Type'] = multi_obj.content_type
                res, status_code = exec_main(method, url, multi_obj, header)
                if fp:
                    fp.close()
                    try:
                        os.remove(file_path)
                    except Exception as e:
                        logger.info(str(e))
            else:
                res, status_code = exec_main(method, url, data, header)
            i['responseData'] = json.loads(res)
        except Exception as e:
            logger.info(str(e))
    return depend_list


def file_req_data(file_key, file_name, fp, case_data):
    """
    # 生成上传文件请求数据
    :param file_key:
    :param file_name:
    :param fp:
    :param case_data:
    :return:
    """
    try:
        multi_fields = dict()
        try:
            if not file_key:
                file_key = 'file'
            file_dict = {file_key: (file_name, fp)}
            multi_fields.update(file_dict)
        except:
            if file_key:
                multi_fields.update(json.loads(file_key))
        if case_data:
            multi_fields.update(case_data)
        multi_obj = MultipartEncoder(fields=multi_fields)
    except Exception as e:
        multi_obj = None
        logger.info(str(e))

    return multi_obj


def assert_result(status_code, response, assert_status_code, assert_list):
    """
    # 结果断言
    :param status:
    :param response:
    :return:
    """
    if status_code != assert_status_code:
        return False
    # 断言
    assert_obj = AssertResult()
    flag = assert_obj.assertMain(assert_list, response)
    return flag


def exec_main(method, url, data, header):
    """
    # 执行测试主程序
    :param method:
    :param url:
    :param data:
    :param header:
    :return:
    """
    req_obj = RunMethod()
    res = req_obj.run_main(method, url, data, header)
    return res, req_obj.get_status_code()


def update_res_params_to_dict(res, res_params_list, rely_data_dict):
    """
    # 更新新的返回结果参数到参数字典中
    :param res:
    :param res_params_list:
    :param rely_data_dict:
    :return:
    """
    res_multi_obj = MultiDepend()
    if isinstance(res, str):
        try:
            res2 = json.loads(res)
        except:
            res2 = dict()
    else:
        res2 = res
    for i in res_params_list:
        paramName = i.get('paramName')
        searchKey = i.get('relyData').get('searchKey')
        searchValue = i.get('relyData').get('searchValue')
        # 将依赖数据填入searchValue
        try:
            searchValue, used_depend_dict, code, not_found_depend_list = format_str(searchValue, rely_data_dict)
        except:
            pass
        getKey = i.get('relyData').get('getKey')
        try:
            rely_data_dict[paramName] = res_multi_obj.get_rely_value_recur(res2, searchKey, searchValue, getKey)
        except Exception as e:
            logger.info(str(e))


def update_var_dict_to_db(user_obj, pro_obj, var_dict):
    """
    # 更新用户变量字典
    :param request:
    :param pro_obj:
    :return:
    """
    if not pro_obj:
        return False
    product = pro_obj.product
    user_var_obj = UserVariables.objects.filter(user_ref=user_obj, product=product).first()
    if not user_var_obj:
        user_var_obj = UserVariables(user_ref=user_obj, product=product)
    # user_var_obj.varDict = var_dict
    # 整合新变量字典
    temp_dict = dict()
    temp_dict.update(**(user_var_obj.varDict))
    temp_dict.update(**var_dict)
    user_var_obj.varDict = temp_dict
    user_var_obj.save()


def update_public_var_dict(pro_obj, var_dict, username='public'):
    """
    # 更新用户变量字典到公共用户
    :param pro_obj:
    :param var_dict:
    :param username:
    :return:
    """
    if not pro_obj:
        return False
    try:
        user_obj = User.objects.filter(username=username).first()
        if not user_obj:
            user_obj = User(username=username, password='123456', isAdmin=False)
            user_obj.save()
        product = pro_obj.product
        user_var_obj = UserVariables.objects.filter(user_ref=user_obj, product=product).first()
        if not user_var_obj:
            user_var_obj = UserVariables(user_ref=user_obj, product=product)
        # 整合新变量字典
        temp_dict = dict()
        temp_dict.update(**(user_var_obj.varDict))
        temp_dict.update(**var_dict)
        user_var_obj.varDict = temp_dict
        user_var_obj.save()
    except:
        pass


def get_public_var_dict(pro_obj, username='public'):
    """
    # 获取公共用户变量字典
    :param pro_obj:
    :param username:
    :return:
    """
    if not pro_obj:
        return dict()
    user_obj = User.objects.filter(username=username).first()
    if not user_obj:
        return dict()
    product = pro_obj.product
    user_var_obj = UserVariables.objects.filter(user_ref=user_obj, product=product).first()
    if not user_var_obj:
        user_var_obj = UserVariables(user_ref=user_obj, product=product)
    user_var_dict = user_var_obj.varDict
    return user_var_dict
