import datetime
import uuid
import re
from sqlalchemy.orm.attributes import flag_modified
from flask_mail import Message
from ec.ext import db, celery, mail
from libs.utils.assert_result import AssertResult
from libs.utils.multi_depend import get_params_to_dict
from ec.account import User
import time


@celery.task
def scenario_case_set_execute(**args):
    from ec.iot_sdk.model import SdkCaseSet, SdkCase, SdkResult, SdkResultMeta, SdkScenarioTaskResult, SdkScenarioTask
    task_id = args.get('id')
    scenario_id = args.get('scenario_id')
    server_id = args.get('server_id')
    project_id = args.get('project_id')
    server_ip = args.get('server_ip')
    case_sets = args.get('case_sets_id')
    result_ids = []
    user_id = args.get('user_id')
    case_num = 0
    set_pass = 1
    record_id = str(uuid.uuid4())

    record = SdkScenarioTaskResult(
        id=record_id,
        result_ids=result_ids,
        status=0,
        # user_id=case_set.user_id,
        scenario_task_id=task_id,
        scenario_id=scenario_id,
        server_ip=server_ip,
        project_id=project_id,
        spend=0,
        is_pass=set_pass,
        success_num=0,
        total_num=0
    )
    db.session.add(record)

    for set_id in case_sets:
        result_id = str(uuid.uuid4())
        result_ids.append(result_id)
        case_set = SdkCaseSet.find_by_id(set_id)
        cases = []
        for case_id in case_set.case_ids:
            case = SdkCase.query.filter(SdkCase.id == case_id).first()
            if case:
                cases.append(case)

        result = SdkResult(
            id=result_id,
            status=0,
            case_set_id=case_set.id,
            server_id=server_id,
            user_id=case_set.user_id,
            project_id=case_set.project_id
        )
        db.session.add(result)
        rm_ids = []
        for index, case in enumerate(cases):
            rm = SdkResultMeta(
                status=0,
                step=index,
                result_id=result_id,
                case_id=case.id
            )
            db.session.add(rm)
            db.session.commit()
            rm_ids.append(rm.id)
            case_num += 1
        delay_time = 0

        for rm_id in rm_ids:
            scenario_result_meta_execute.apply_async(args=[record_id, result_id, rm_id], countdown=delay_time)
            delay_time += 2
        db.session.commit()

    time.sleep(case_num * 2 + 30)
    record = SdkScenarioTaskResult.find_by_id(record_id)
    record.result_ids = result_ids
    flag_modified(record, 'result_ids')
    db.session.commit()
    pass_rate = 0
    set_pass = 1
    for result_id in result_ids:
        record = SdkScenarioTaskResult.find_by_id(record_id)
        result = SdkResult.find_by_id(result_id)
        result.status = 1
        record.success_num += SdkResultMeta.get_count(db.session.query(SdkResultMeta). \
                                                      filter(SdkResultMeta.result_id == result_id). \
                                                      filter(SdkResultMeta.status == 1))
        record.total_num += SdkResultMeta.get_count(
            db.session.query(SdkResultMeta).filter(SdkResultMeta.result_id == result_id))
        db.session.commit()
    record = SdkScenarioTaskResult.find_by_id(record_id)
    if record.total_num > 0:
        pass_rate = record.success_num / record.total_num
    if pass_rate < 0.9:
        set_pass = 0
    record.is_pass = set_pass
    record.status = 1
    db.session.commit()
    task = SdkScenarioTask.find_by_id(task_id)
    title = task.name
    content = "执行{result},共{total}条用例，其中成功{success}条，失败{fail}条".format(result='通过' if set_pass else '失败',
                                                                       success=record.success_num,
                                                                       total=record.total_num,
                                                                       fail=record.total_num - record.success_num)
    email = dict()
    email['title'] = title
    email['content'] = content
    send_email(user_id, **email)

    return {}


def send_email(user_id, **result):
    user = User.find_by_id(user_id)
    msg = Message(
        'IOT-sdk场景测试任务执行情况',
        # recipients=[user.email]
        recipients=['wangqiao@megvii.com']
    )
    msg.html = '''
        <html>
        <head>IOT-sdk场景测试任务"{}"执行情况</head>
        <body>
        <p>IOT-sdk场景测试任务执行完成<br>
        执行结果: {}<br>
        详情请去天狼效率中台查询
        </p>
        </body>
        </html>
                '''.format(result.get('title'), result.get('content'))

    mail.send(msg)


@celery.task
def scenario_result_meta_execute(record_id, result_id, rm_id):
    from ec.iot_sdk.model import SdkCaseSet, SdkCase, \
        SdkResult, SdkResultMeta, SdkScenarioTaskResult
    result = SdkResult.find_by_id(result_id)
    rm = SdkResultMeta.find_by_id(rm_id)

    case = SdkCase.find_by_id(rm.case_id)
    kwargs = {
        'user_id': result.user_id,
        'server_id': result.server_id
    }
    request_body, request_result, assert_result = execute_case(case, **kwargs)
    record = SdkScenarioTaskResult.find_by_id(record_id)
    request_body.pop('sp', None)
    rm.start_at = datetime.datetime.now()
    if assert_result:
        rm.status = 1
        rm.end_at = datetime.datetime.now()
        rm.assert_result = assert_result
        rm.request_body = request_body
        rm.response_body = request_result
        flag_modified(rm, 'request_body')
        flag_modified(rm, 'response_body')
        db.session.commit()

    else:
        rm.status = 2
        rm.end_at = datetime.datetime.now()
        rm.assert_result = assert_result
        rm.request_body = request_body
        rm.response_body = request_result
        flag_modified(rm, 'request_body')
        flag_modified(rm, 'response_body')
        db.session.commit()
    result.end_at = datetime.datetime.now()
    result.spend_time = result.spend_time + (rm.end_at - rm.start_at).seconds
    record.spend += (rm.end_at - rm.start_at).microseconds

    db.session.commit()


def execute_case(case, **kwargs):
    from ec.iot_sdk.model import SdkConstantParam, SdkParam

    user_id = kwargs.get('user_id')
    str_params = str(case.params)
    params, total = SdkConstantParam.get_params_by_query(user_id=user_id)
    for param in params:
        if param.value is not None:
            str_params = str_params.replace('{' + param.name + '}', param.value)
        else:
            str_params = str_params.replace('{' + param.name + '}', 'None')

    it = re.finditer(r"{.*?}", str_params[1: len(str_params) - 2])

    values = []
    for i in it:
        values.append(i.group())

    data = eval(str_params)
    for key, value in data.items():
        if value in values:
            data[key] = None

    print('--------------参数--------------')
    print(str_params)
    args = {'data': eval(str_params), 'server_id': kwargs.get('server_id')}
    print('interface', case.interface)
    result = case.interface.execute_interface(**args)

    # 断言校验
    print('---------断言校验-------------')
    assert_result = verify_assert_result(case, result)
    print(assert_result)
    print(case)
    if not assert_result:
        return args['data'], result, assert_result

    # 置换parmas
    interface_params, total = SdkParam.get_params_by_query(
        case_id=case.id,
        type=1
    )
    data = result
    for param in interface_params:
        try:
            res_parm_list = [
                {
                    "paramName": param.name,
                    "relyData": {
                        "searchKey": param.search_key if param.search_key else '',
                        "searchValue": param.search_value if param.search_key else '',
                        "getKey": param.key if param.key else ''
                    }
                }
            ]
            value = get_params_to_dict(res=data, res_params_list=res_parm_list)
            if value is not None:
                param.value = value
                constant_param = SdkConstantParam.get_param_by_name(param.name)
                if constant_param:
                    constant_param.value = value
                else:
                    constant_param = SdkConstantParam(
                        name=param.name,
                        value=value,
                        type=param.type,
                        case_id=param.case_id,
                        user_id=param.user_id
                    )
                    db.session.add(constant_param)
                db.session.commit()
        except Exception as e:
            print(e)
    return args['data'], result, assert_result


def verify_assert_result(case, response):
    assert_list = []

    for ass in case.asserts:
        temp_assert = {
            "assertMethod": ass.method,
            "compKey": ass.key,
            "expectType": ass.type,
            "expectResult": ass.result
        }
        assert_list.append(temp_assert)

    ar = AssertResult()
    result = ar.assertMain(assert_list, response)
    return result
