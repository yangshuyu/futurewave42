import json
import unittest


class AssertResult:

    def assert_single(self, assert_method, ex_result, response, ex_type=None, comp_key=None):
        """
        执行单个断言
        :param assert_method: 断言方法
        :param ex_result: 期望的结果
        :param response: 请求返回数据
        :param ex_type: 期望结果的类型
        :param comp_key: 需要和返回数量里哪个键的值进行对比
        :return: 返回断言结果，True或False
        """
        flag = False
        re_result = None

        try:
            # 优化结果和断言方法
            if ex_type:
                if ex_type == 'str':
                    ex_result = str(ex_result)
                else:
                    ex_result = eval(str(ex_type) + '(' + str(ex_result) + ')')
            if isinstance(response, str):
                resp_dict = json.loads(response)
            else:
                resp_dict = response
            if assert_method not in dir(unittest.TestCase):
                assert_method = 'assertEqual'

            # 调用断言
            flag = self.assert_recur(assert_method, ex_result, resp_dict, comp_key)
            return flag
        except:
            return False

    def assert_recur(self, assert_method, ex_result, re_result, islist):
        """
        # 断言递归，主要是针对有列表的情况，比如需要查找一个列表中某个值下是否有某个字段，有可能下面还有列表
        :param assert_method: 断言方法
        :param ex_result: 期望结果
        :param re_result: 实际结果
        :param islist: 键值序列，判断走到哪一层了，None的时候表示已经到头，可以直接进行断言了，否则说明有列表，需要递归
        :return: 断言结果
        """
        flag = False
        assert_obj = unittest.TestCase()

        try:
            re_result, islist = self.get_nested_value(re_result, islist)
            # 对于列表，递归
            if isinstance(re_result, list) and islist is not None:
                for i in re_result:
                    flag = self.assert_recur(assert_method, ex_result, i, islist)
                    if flag is True:
                        return flag
                return flag
            # 如果没有列表，直接往下走，进行断言
            # 断言分类
            assert_compare_list = ['assertAlmostEqual', 'assertAlmostEquals', 'assertCountEqual',
                                   'assertDictContainsSubset', 'assertDictEqual', 'assertEqual', 'assertEquals',
                                   'assertGreater', 'assertGreaterEqual', 'assertIn', 'assertIs', 'assertIsNot',
                                   'assertLess', 'assertLessEqual', 'assertListEqual', 'assertLogs',
                                   'assertMultiLineEqual', 'assertNotAlmostEqual', 'assertNotAlmostEquals',
                                   'assertNotEqual', 'assertNotEquals', 'assertNotIn', 'assertNotRegex',
                                   'assertNotRegexpMatches', 'assertRaises', 'assertRaisesRegex',
                                   'assertRaisesRegexp',
                                   'assertRegex', 'assertRegexpMatches', 'assertSequenceEqual',
                                   'assertSetEqual',
                                   'assertTupleEqual', 'assertWarns', 'assertWarnsRegex', ]
            assert_bool_list = ['assertFalse', 'assertTrue', 'assertIsNone', 'assertIsNotNone', ]
            assert_instance_list = ['assertIsInstance', 'assertNotIsInstance', ]

            # 分类判断结果
            if assert_method in assert_compare_list:
                if type(ex_result) == list:
                    getattr(assert_obj, assert_method)(re_result, ex_result)
                else:
                    getattr(assert_obj, assert_method)(ex_result, re_result)
            elif assert_method in assert_bool_list:
                getattr(assert_obj, assert_method)(re_result)
            elif assert_method in assert_instance_list:
                getattr(assert_obj, assert_method)(re_result, eval(ex_result))
            flag = True
        except:
            flag = False
        return flag

    def get_nested_value(self, orig_dict, nested_key):
        """
        # 根据关键词组合查找嵌套的值，比如a.b意味着找字典的a值（又是字典），然后从a值中找b的值
        :param orig_dict:
        :param nested_key:
        :return:
        """
        key_list = None
        ret_value = orig_dict
        try:
            if '.' in nested_key:
                key_list = nested_key.split('.')
                j = 0
                for i in key_list:
                    if isinstance(ret_value, list):
                        try:
                            i = int(i)
                        except:
                            return ret_value, '.'.join(key_list[j:])
                    ret_value = ret_value[i]
                    j += 1
            else:
                ret_value = orig_dict.get(nested_key, None)
        except:
            return None, None
        return ret_value, None

    def assertMain(self, assert_json, response):
        """
        主函数，对断言json进行解析，并调用assert_single执行每次断言
        :param assert_json: 断言json，是列表，每一项都是字典格式，字典键值固定，内容自定义
        :param response: 请求返回结果
        :return: 断言结果
        """
        try:
            if not assert_json or not isinstance(assert_json, list):
                return True
            for i in assert_json:
                assert_method = i.get('assertMethod')
                ex_result = i.get('expectResult')
                ex_type = i.get('expectType')
                comp_key = i.get('compKey')
                if not self.assert_single(assert_method, ex_result, response, ex_type, comp_key):
                    return False
            return True
        except:
            return False
