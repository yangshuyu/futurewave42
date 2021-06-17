import datetime
import json
import math
import time

import hashlib

import os
import requests
from requests_toolbelt import MultipartEncoder

from ec.ext import celery, db
from ec.galaxy_folder_manage.model import GalaxyFolder
from ec.galaxy_library_manage.model import GalaxyLib, GalaxyLibMete
from ec.testcenter.utils.dynamic_params import DynamicParams
from libs.utils.functions import format_func
from libs.utils.multi_depend import format_str


@celery.task
def execute_create_galaxy_library(**kwargs):
    galaxy_server_ip = kwargs.get("server")
    lib_num = kwargs.get("lib_num")
    lib_type = kwargs.get("lib_type", "1")
    lib_name = kwargs.get("lib_name", "")
    username = kwargs.get("username")
    type = kwargs.get("type")


    req = {
        "audio": {"id": "1222"},
        "auth": {"type": "2", "accredit": "6e9232ef-7b84-11e8-86b1-6c92bf4e6960"},
        "carType": "1",
        "cascadeAuth": "2",
        "lv": "1",
        "tag": {},
    }
    # 查找服务的详细信息
    if lib_type == "1":  # 人脸底库
        req["type"] = str(type)
        req["deployObject"] = 1
    elif lib_type == "2":  # 人体底库
        req["type"] = str(type)
        req["deployObject"] = "2"
    elif lib_type == "3":  # 机动车底库
        req["deployObject"] = "3"
    elif lib_type == "4":  # 非机动车底库
        req["carType"] = "2"
        req["deployObject"] = "5"

    url = "http://{}/api/galaxy/v1/album".format(galaxy_server_ip)
    headers = {'Content-Type': 'application/json;charset=UTF-8',
               "Module-Source": "video-structure-realtime-web",
               'authorization': '59dacfac729esuperadmin427f90bfa98c0a636e0c'}

    gl = GalaxyLib(
        creater=username,
        lib_type=lib_type,
        lib_name=lib_name,
        lib_num=lib_num,
        type=type,
        server=galaxy_server_ip
    )
    db.session.add(gl)
    db.session.commit()

    succeed_num = 0
    error_num = 0
    base_dict = {"number":0}
    for x in range(int(lib_num)):
        # 组装底库名称
        # searchValue, used_depend_dict = format_str(searchValue, rely_data_dict)
        # dynamic_vars_obj = DynamicParams()
        # var_dict.update(**(dynamic_vars_obj.get_time_dict(datetime.datetime.now())))
        # # 加入实时随机变量
        # var_dict.update(**(dynamic_vars_obj.gen_real_random_number()))
        #
        new_name ,base_dict,b,c,d= format_func(lib_name,base_dict)
        req["name"] = new_name
        response = requests.post(url, data=json.dumps(req), headers=headers).json()
        msg = ""
        lib_id = ""
        msg = response.get("msg")
        if response.get("code") == 0:
            succeed_num += 1
            lib_id =  response.get("data",{}).get("id")
            glm = GalaxyLibMete(
                creater=username,
                lib_type=lib_type,
                lib_name=req["name"],
                msg=msg,
                lib_id=lib_id,
                index=x+1,
                gal_ref=gl.id,
                server=galaxy_server_ip
            )
            db.session.add(glm)
        else:
            error_num += 1
            glm = GalaxyLibMete(
                creater=username,
                lib_type=lib_type,
                lib_name=req["name"],
                msg=msg,
                lib_id=lib_id,
                index=x + 1,
                gal_ref=gl.id,
                server=galaxy_server_ip
            )
            db.session.add(glm)
    gl.succeed_num = succeed_num
    gl.error_num = error_num
    db.session.commit()

    return





chunksize = 10485760

def getFileSize(file):  # 获取视频文件和切片文件大小\
    file_all_size = os.path.getsize(file)  # 文件总大小
    totalChunkCount = math.ceil(int(file_all_size) / chunksize)  # 文件切块数
    lastchunkSize = file_all_size % chunksize  # 文件切块最后一块的大小
    return file_all_size, totalChunkCount, lastchunkSize

def upload_progress(server_ip, headers, file_name, md5, file_all_size, chunkCount, dirId):
    requrl = "http://{}/api/galaxy/v1/file/files:progress".format(server_ip)
    data = [{
        "fileMd5": md5,
        "chunkCount": chunkCount,
        "fileName": file_name,
        "fileSize": file_all_size,
        "dirId": dirId,
        'parentId': dirId,
        'totalChunks':chunkCount,
    }]
    r = requests.post(requrl, data=json.dumps(data), headers=headers)
    result = r.json()

    if result['data']:
        uploadToken = result['data'][0]['fileId']
    return uploadToken


def upload_chunk(server_ip, headers, file_name, md5, file_all_size, totalChunkCount, uploadToken, index, chunk, chunksize,
                 currentChunkSize):
    requrl = "http://{}/api/galaxy/v1/file/files:create".format(server_ip)
    files = {
        'currentChunkIndex': str(index + 1),
        'chunkSize': str(chunksize),
        'currentChunkSize': str(currentChunkSize),
        'fileSize': str(file_all_size),
        'fileMd5': md5,
        'fileName': file_name,
        'fileId': uploadToken,
        'totalChunkCount': str(totalChunkCount),
        'file': (file_name, chunk, "video/vnd.dlna.mpeg-tts")
    }

    m = MultipartEncoder(fields=files)
    headers['Content-Type'] = m.content_type

    r = requests.post(requrl, headers=headers, data=m)
    result = r.json()
    headers['Content-Type'] = 'application/json;charset=UTF-8'
    if result['code'] == 0:
        return True
    else:
        return False




#
# @celery.task
# def execute_create_galaxy_folder(**kwargs):
#     galaxy_server_ip = kwargs.get("server")
#     dmp_addr = kwargs.get("dmp_addr")
#     folder_name = kwargs.get("folder_name")
#     folder_ids = kwargs.get("folder_id")
#     username = kwargs.get("username")
#     file_addr = kwargs.get("file_addr")
#     parent_name = kwargs.get("parent_name")
#
#     if folder_ids:
#         folder_f_id = folder_ids[-1]
#     else:
#         folder_f_id = "0"
#
#     headers = {'Content-Type': 'application/json;charset=UTF-8',
#                'authorization': '59dacfac729esuperadmin427f90bfa98c0a636e0c'}
#     # 如果文件名称存在 就创建文件夹 再上传 否则就直接上传
#     if folder_name:
#
#         url = 'http://{}/api/galaxy/v1/file/files:folderCreate'.format(galaxy_server_ip)
#         # 查询父级文件夹名称
#         body = {"name": folder_name, "parentId": str(folder_f_id)}
#         response = requests.post(url, data=json.dumps(body), headers=headers).json()
#         id_url = 'http://{}/api/galaxy/v1/file/files'.format(galaxy_server_ip)
#         id_res = {
#             "dirId": '0',
#             "fileName": folder_name,
#             "pageNo": 1,
#             "pageSize": 20,
#             "status": 1,
#         }
#         id_response = requests.post(id_url, data=json.dumps(id_res), headers=headers).json()
#         up_folder_id = id_response.get("data").get("records")[0].get("id")
#     else:
#         up_folder_id = folder_f_id
#
#
#     file_name =  file_addr.split("/")[-1]
#     # 开始上传操作
#     with open(file_addr, "rb") as f:
#         file = f.read()
#     file_md5 = hashlib.md5(file).hexdigest()
#     (file_all_size, totalChunkCount, lastchunkSize) = getFileSize(file_addr)
#     uploadToken = upload_progress(galaxy_server_ip, headers, file_name, file_md5, file_all_size, totalChunkCount, up_folder_id)
#     with open(file_addr, "rb") as f:
#         index = 0
#         while True:
#             chunk = f.read(chunksize)
#             if (chunk):
#                 if index + 1 == totalChunkCount:
#                     currentChunkSize = lastchunkSize
#                 else:
#                     currentChunkSize = chunksize
#                 upload_chunk(galaxy_server_ip, headers, file_name, file_md5, file_all_size, totalChunkCount, uploadToken,
#                              index, chunk, chunksize, currentChunkSize)
#                 index = index + 1
#             else:
#                 break
#
#     # 保存信息
#     gf = GalaxyFolder(
#         creater = username,
#         folder_name = folder_name,
#         folder_parent_name = parent_name,
#         file_addr = dmp_addr,
#         server = galaxy_server_ip,
#         status = "成功",
#     )
#     db.session.add(gf)
#     db.session.commit()
#
#

