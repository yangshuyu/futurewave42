# -*- coding:utf-8 -*-
import base64
import json
import os
import re
import random

# from apiAuto.models import CustomFunction

all_funcs = locals()



def generate_ordered_number(m, n=1):
    """
    # 产生有序的数列，每次返回一个数字，支持自增，自减，自定义步长三种形式
    :param m:起始值，每执行一次函数，更新为m+n
    :param n:步长，例如为1时，每次产生的数字加1
    :return: m+n 指定规则产生的数字
    """

    return int(m) + int(n)


def format_func(tar_str, var_dict):
    """
    # 格式化字符串，支持{{ }},{ }, %()s三种形式
    :param tar_str:
    :param var_dict:
    :return:
    """
    code = 0
    msg = ''
    number = 0
    not_found_depend_list = []
    used_depend_dict = dict()
    tar_str = tar_str.replace('\n', '')
    reg = re.compile("\$\$\{\{(.*)\}\}")
    match_list = reg.findall(tar_str)
    for i in match_list:
        if 'generate_ordered_number(' in i:
            pattern = re.compile(r'[(](.*)[)]')
            a = re.findall(pattern, i)[0].split(',')
            m = 'number'
            number = var_dict.get(m)
            new_data = eval(i)  # 执行过程中自动加__builtins__属性
            var_dict.update({m: new_data})
        else:
            # print('11111',i)
            new_data = eval(i, var_dict, all_funcs)
            # print(1232)
            # print(new_data)
            # new_data = ''
            # print('000000')
            # exec('new_data2 = "123"')
            # new_data3 = locals()['new_data2']
            # print('1====')
            # print('1====', new_data3)
            #
            #
            # print('1111')
            # custom_obj = CustomFunction.objects.filter(function_name='generate_ordered_number2').first()
            # print('1111',custom_obj.content)
            # c = custom_obj.content + '\n' + 'all_funcs = locals()'+ '\n'+'new_data4 = eval(i, var_dict, all_funcs)'+'\n'+'print("nnnn",new_data)'
            #
            # # print(eval(i, var_dict, all_funcs))
            # print(c,'-------------------------')
            # try:
            #     # print(eval(i, var_dict, all_funcs))
            #     # print(locals())
            #     print(exec(c))
            #     new_data5= locals()['new_data4']
            #     print('4====',new_data5)
            #
            # except Exception as e:
            #     print('222',e)
        tar_str = tar_str.replace("$${{%s}}" % i, str(new_data))
        index = i.find('(')
        # print(index,'iii')
        if index != -1:
            used_depend_dict[i[0:index]] = str(new_data)
        else:
            used_depend_dict[i] = str(new_data)


    return tar_str, var_dict, code, not_found_depend_list, msg

if __name__ == '__main__':

  for x in range(int(3)):
        print(base_dict)
        new_name ,base_dict,b,c,d= format_func(lib_name,base_dict)
        print(new_name ,base_dict,b,c,d,333333333333333333333333)