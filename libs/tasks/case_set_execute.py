import datetime
import re
import uuid

from sqlalchemy.orm.attributes import flag_modified

from ec.ext import db, celery
from libs.utils.assert_result import AssertResult
from libs.utils.multi_depend import get_params_to_dict


@celery.task
def case_set_execute(result_id, set_id, server_id):
    from ec.iot_sdk.model import SdkCaseSet, SdkCase, \
        SdkResult, SdkResultMeta

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
    rms = []
    for index, case in enumerate(cases):
        rm = SdkResultMeta(
            status=0,
            step=index,
            result_id=result_id,
            case_id=case.id
        )
        db.session.add(rm)
        rms.append(rm)
    db.session.commit()
    delay_time = 0

    for rm in rms:
        result_meta_execute.apply_async(args=[result_id, rm.id], countdown=delay_time)
        delay_time += 2

    db.session.commit()


@celery.task
def result_meta_execute(result_id, rm_id):
    from ec.iot_sdk.model import SdkCaseSet, SdkCase, \
        SdkResult, SdkResultMeta
    result = SdkResult.find_by_id(result_id)
    rm = SdkResultMeta.find_by_id(rm_id)

    case = SdkCase.find_by_id(rm.case_id)
    kwargs = {
        'user_id': result.user_id,
        'server_id': result.server_id
    }

    request_body, request_result, assert_result = execute_case(case, **kwargs)
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

        result.status = 1
        result.end_at = datetime.datetime.now()

        db.session.commit()

    rm.end_at = datetime.datetime.now()
    result.spend_time = result.spend_time + (rm.end_at - rm.start_at).seconds
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
