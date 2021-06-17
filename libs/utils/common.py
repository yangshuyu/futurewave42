# -*- coding: utf-8 -*-
# Created by Duanwei on 2020/8/7
import math
import random
import string
from datetime import datetime, timedelta


def changeTime(allTime):
    day = 24 * 60 * 60
    hour = 60 * 60
    min = 60
    if allTime < 60:
        return "%d sec" % math.ceil(allTime)
    elif allTime > day:
        days = divmod(allTime, day)
        return "%d d, %s" % (int(days[0]), changeTime(days[1]))
    elif allTime > hour:
        hours = divmod(allTime, hour)
        return "%d h, %s" % (int(hours[0]), changeTime(hours[1]))
    else:
        mins = divmod(allTime, min)
        return "%d m, %d s" % (int(mins[0]), math.ceil(mins[1]))


def get_weeks(begin_date, end_date):
    date_week = []
    date_list = []
    dt = datetime.strptime(begin_date, "%Y-%m-%d")
    date = begin_date
    while date <= end_date:
        date_list.append(date)
        dt = dt + timedelta(1)
        date = dt.strftime("%Y-%m-%d")
    for i in date_list:
        dt = datetime.strptime(i, "%Y-%m-%d")
        if dt.weekday() == 0:
            sunday = (dt + timedelta(days=6)).strftime('%Y-%m-%d')
            date_week.append([i, sunday])
    if date_week[0][0] != date_list[0]:
        monday = datetime.strptime(date_list[0], "%Y-%m-%d")
        one_day = timedelta(days=1)
        while monday.weekday() != 0:
            monday -= one_day
        sunday = (monday + timedelta(days=6)).strftime('%Y-%m-%d')
        date_week.insert(0, [monday.strftime('%Y-%m-%d'), sunday])
    now = datetime.now()
    if len(date_week) > 0:
        last_day = datetime.strptime(date_week[len(date_week) - 1][1], "%Y-%m-%d")
        if last_day > now:
            date_week[len(date_week) - 1][1] = now.strftime('%Y-%m-%d')
    return date_week


def get_before_date(end_time, j):
    yyyy = int(((end_time.year * 12 + end_time.month) - j) / 12)
    mm = int(((end_time.year * 12 + end_time.month) - j) % 12)
    if mm == 0:
        yyyy -= 1
        mm = 12
    last_start_time = datetime(yyyy, mm, 1).strftime("%Y-%m-%d")
    return last_start_time



def result_to_dict(result):
    dict_data = dict()
    data_fields = getattr(result, "_fields")
    for key in data_fields:
        dict_data[key] = getattr(result, key)
    return dict_data

def get_week_monday_and_sunday_by_date(now_time):
    """
    给定一个日期-返回日期所在周的周一0点时间 和 周日23点59分59秒
    :param date_str: 如："2020-05-01"
    :return: 给定一个日期-返回日期所在周的周一0点时间 和 周日23点59分59秒
    """
    # now_time = date_str
    week_start_time = now_time - timedelta(days=now_time.weekday(), hours=now_time.hour, minutes=now_time.minute, seconds=now_time.second, microseconds=now_time.microsecond)
    week_end_time = week_start_time + timedelta(days=6, hours=23, minutes=59, seconds=59)
    return week_start_time, week_end_time


def get_last_week_monday_and_sunday_by_date(now_time):
    """
    给定一个日期-返回日期所在周的周一0点时间 和 周日23点59分59秒
    :param date_str: 如："2020-05-01"
    :return: 给定一个日期-返回日期所在周的周一0点时间 和 周日23点59分59秒
    """
    # now_time = date_str
    week_end_time = now_time - timedelta(days=now_time.weekday(), hours=now_time.hour, minutes=now_time.minute, seconds=now_time.second, microseconds=now_time.microsecond)
    week_start_time = week_end_time - timedelta(days=6, hours=23, minutes=59, seconds=59)
    return week_start_time, week_end_time


def get_server_password(min_length=12, max_length=16):
    length = random.randint(min_length, max_length)
    letters = string.ascii_letters + string.digits  # alphanumeric, upper and lowercase
    return ''.join([random.choice(letters) for _ in range(length)])
