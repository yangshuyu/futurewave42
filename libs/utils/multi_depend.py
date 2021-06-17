# coding:utf-8
# from apiAuto.utils.logger import Logger as logger
import json
import re


class MultiDepend:

    def __init__(self):
        """
        # 多个依赖数据处理类
        """
        self.url_params = []
        self.fill_in = {}

    def get_nested_value(self, orig_dict, nested_key):
        """
        # 根据关键词组合查找嵌套的值，比如a.b意味着找字典的a值（又是字典），然后从a值中找b的值
        :param orig_dict:
        :param nested_key:
        :return:
        """
        key_list = None
        ret_value = orig_dict
        parent_dict = ret_value
        try:
            if '.' in nested_key:
                key_list = nested_key.split('.')
                j = 0
                for i in key_list:
                    if isinstance(ret_value, list):
                        try:
                            i = int(i)
                        except:
                            return ret_value, '.'.join(key_list[j:]), parent_dict
                    parent_dict = ret_value
                    ret_value = ret_value[i]
                    j += 1
            else:
                ret_value = orig_dict.get(nested_key, None)
        except:
            return None, None, parent_dict
        return ret_value, None, parent_dict

    def get_rely_value(self, search_key, search_value, get_fill_dict, response_data):
        """
        # 查找依赖值
        :param search_key:
        :param search_value:
        :param get_fill_dict:
        :param response_data:
        :return:
        """
        try:
            # 递归获取依赖数据，主要是针对有嵌套列表的情况
            for i in get_fill_dict:
                get_key = i.get('name')
                fill_in_list = i.get('fillIn')
                # 如果只是单纯执行用例，不需要查找值
                if not fill_in_list:
                    continue
                rely_value = self.get_rely_value_recur(response_data, search_key, search_value, get_key)
                if not rely_value:
                    print("查找依赖数据%s时出错，case失败" % search_key)
                    return None
                print("成功查找到case的依赖数据为%s" % rely_value)
                for j in fill_in_list:
                    if j.lower() == '$url':
                        self.url_params.append(rely_value)
                    else:
                        self.fill_in[j] = rely_value
            return True
        except Exception as e:
            print("获取依赖数据时出错，case失败: %s" % str(e))
            return None

    def get_rely_value_recur(self, rely_result, islist, rely_find_value, rely_key):
        """
        # 递归查找返回值，主要是针对数组嵌套的情况
        :param rely_result: 响应body
        :param islist: 字典键值层，例如：a.b.c
        :param rely_find_value: 需要查找的值
        :param rely_key: 需要获取的键值
        :return: 要获取的值
        """
        rely_value = None
        try:
            # 如果islist是None，就是完全不需要查找，直接取值
            if not islist:
                rely_value, rely_key, parent_dict = self.get_nested_value(rely_result, rely_key)
                # if rely_key or rely_value is dict or rely_value is list:
                if rely_key:
                    return None
                else:
                    return rely_value
            # 否则，正常查找
            rely_result, islist, parent_dict = self.get_nested_value(rely_result, islist)
            # 对于列表，递归
            if isinstance(rely_result, list):
                if islist:
                    for i in rely_result:
                        rely_value = self.get_rely_value_recur(i, islist, rely_find_value, rely_key)
                        if rely_value:
                            return rely_value
                    return rely_value
            # 如果没有列表，判断是否是字典，如果是字典，说明islist肯定已经到头了，此时有可能不需要查找，直接取值
            elif isinstance(rely_result, dict):
                rely_value = self.get_nested_value(rely_result, rely_key)[0]
                return rely_value
            # 除此之外，说明已经找到值了，这时候进行判断是不是想要找的值
            else:
                if str(rely_result) == str(rely_find_value):
                    rely_value = self.get_nested_value(parent_dict, rely_key)[0]
                else:
                    rely_value = None
                return rely_value
        except Exception as e:
            print("获取依赖数据时出错，case失败: " + str(e))
        return rely_value

    def update_rely_value(self, json_key, rely_value, request_json_data):
        """
        # 更新依赖数值到json中
        :param json_key:
        :param rely_value:
        :param request_json_data:
        :return:
        """
        print("更新结果到json data")
        # 如果是非string类型，直接更新完返回
        if not isinstance(json_key, str):
            try:
                json_key = int(json_key)
                request_json_data[json_key] = rely_value
            except Exception as e:
                print("更新case的依赖数据%s时出错，case失败: %s" % (json_key, str(e)))
            return
        self.update_to_json(json_key, rely_value, request_json_data)

    def update_to_json(self, json_key, rely_value, request_json_data):
        """
        # 更新依赖数值到请求数据
        :param json_key:
        :param rely_value:
        :param request_json_data:
        :return:
        """
        json_key_list = None
        try:
            if '.' in json_key:
                json_key_list = json_key.split('.')
            if json_key_list is None:
                request_json_data[json_key] = rely_value
            else:
                # 获取需要更新的那个case的字典
                tempDict = request_json_data
                j = 0
                while j < len(json_key_list) - 1:
                    k = json_key_list[j]
                    j += 1
                    if isinstance(tempDict, list):
                        k = int(k)
                    tempDict = tempDict[k]
                k = json_key_list[j]
                if isinstance(tempDict, list):
                    k = int(k)
                tempDict[k] = rely_value
            print("成功更新case的依赖数据%s" % (json_key))
        except Exception as e:
            print("更新case的依赖数据%s时出错，case失败: %s" % (json_key, str(e)))

    def update_url(self, url):
        """
        # 更新url
        :param url:
        :return:
        """
        url = url.format(*self.url_params)
        return url

    def run_main(self, url, json_data, depend_json):
        """
        # 主函数
        :param url: case的url
        :param json_data: 请求数据
        :param depend_json: 依赖数据json
        :return:
        """
        for i in depend_json:
            response_data = i.get('responseData')
            if not response_data:
                return None
            if isinstance(response_data, str):
                try:
                    response_data = json.loads(response_data)
                except:
                    return None
            for j in i.get('relyData'):
                search_key = j.get('searchKey')
                search_value = j.get('searchValue')
                get_fill_dict = j.get('getKey')
                print("开始查找对case %s的依赖数据" % i['relyCaseId'])
                find_result = self.get_rely_value(search_key, search_value, get_fill_dict, response_data)
                if not find_result:
                    return None
        try:
            url = self.update_url(url)
            for i in self.fill_in:
                self.update_rely_value(i, self.fill_in[i], json_data)
            return url
        except Exception as e:
            print("更新依赖数据出错：" + str(e))
            return None


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


def get_params_to_dict(res, res_params_list):
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
        searchKey = i.get('relyData').get('searchKey')
        searchValue = i.get('relyData').get('searchValue')
        # 将依赖数据填入searchValue
        try:
            searchValue, used_depend_dict = format_str(searchValue, rely_data_dict)
        except:
            pass
        getKey = i.get('relyData').get('getKey')
        try:
            return res_multi_obj.get_rely_value_recur(res2, searchKey, searchValue, getKey)
        except Exception as e:
            print(e)
        return None


if __name__ == '__main__':
    res = {
        "code": 0,
        'result': {"data": [
            {
                "dev_id": [
                ],
                "type": "1"
            },
            {
                "dev_id": ["110000200500000001"],

                "type": "0"
            }
        ]},
    }

    res_parm_list = [
        {
            # "paramName": "dev_id",
            "relyData": {
                # "searchKey": "result.data.type",
                # "searchValue": "0",
                "getKey": "result.data.1.dev_id"
            }
        }
    ]
    a = get_params_to_dict(res=res, res_params_list=res_parm_list)
    print(a)
