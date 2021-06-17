import datetime
import json
import math
import time
from ftplib import FTP

import os

import hashlib
import requests
from requests_toolbelt import MultipartEncoder
from ec.ext import celery, db

from ec.galaxy_library_manage.model import GalaxyUploadLogs, GalaxyLibMete


@celery.task
def execute_upload_file_to_galaxy_lib(**kwargs):
    print(kwargs)
    server_ip = kwargs.get("server")
    file_addr = kwargs.get("file_addr")
    print("file_addrfile_addrfile_addr",file_addr)
    with open(file_addr,"rb") as f:
        file = f.read()
    username = kwargs.get("username")
    lib_type = kwargs.get("lib_type")
    lib_name = kwargs.get("lib_name")
    id = kwargs.get("id")
    lib_id = kwargs.get("lib_id")
    glm_obj = GalaxyLibMete.find_by_id(id)
    type = kwargs.get("type")
    start_at = datetime.datetime.now()
    try:
        headers = {'Content-Type': 'application/json;charset=UTF-8',
                   "Module-Source": "video-structure-realtime-web",
                   'authorization': '59dacfac729esuperadmin427f90bfa98c0a636e0c'}

        foldername = str(int(time.time() * 1000))
        requests.post("http://{}/api/galaxy/v1/album/task:checkName".format(server_ip) ,
                      data=json.dumps({"name": foldername}), headers=headers).json()

        url =  "http://{}/api/galaxy/v1/album/task:photoUploadAnalyze".format(server_ip)
        files = {
            'file': (foldername, file, "video/vnd.dlna.mpeg-tts")
        }
        m = MultipartEncoder(fields=files)
        headers['Content-Type'] = m.content_type
        res = requests.post(url=url, data=m, headers=headers).json()
        print(res)
        headers['Content-Type'] = 'application/json;charset=UTF-8'
        # 生成任务
        url = "http://{}/api/galaxy/v1/album/task".format(server_ip)
        req = {
            "albumId": lib_id,
            "fileName": foldername,
            "fileTempPath": res["data"]["path"],
            "importType": "1",
            "rule": "root",
            "split": "_",
            "name": foldername,
            "uploadType": "PACKAGE",
        }
        if lib_type == "1":
            req["deployObject"] = 1
        elif  lib_type == "2":
            req["deployObject"] = 2
        elif  lib_type == "3":
            req["deployObject"] = 3
        else :
            req["deployObject"] = 5

        res = requests.post(url=url, data=json.dumps(req), headers=headers).json()
        print(res)
        cmt_id = res.get("data").get( "cmtId")
        url =  "http://{}/zuul/api/galaxy/v1/album/task/photo/photoUpload:".format(server_ip) + cmt_id
        res = requests.post(url, headers=headers,
                            data=json.dumps({"cmtId": res.get("data").get("cmtId")})).json()
        print('上传底库成功：', res)

        time.sleep(10)
        url =  "http://{}/api/galaxy/v1/album/task/".format(server_ip)+cmt_id
        res = requests.get(url=url, headers=headers).json()
        print(res)

        for x in range(500):
            if res.get("data").get("status") == "FILE_NOT_UPLOAD":
                time.sleep(3)
            else:
                break


        gul = GalaxyUploadLogs(
            creater=username,
            glm_ref=glm_obj.gal_ref,
            upload_type=type,
            lib_name=lib_name,
            task_name=foldername,
            succeed_num = res.get("data").get("successTotal"),
            error_num= res.get("data").get("errTotal"),
            total_num= res.get("data").get("total"),
            start_at= start_at ,
            end_at= datetime.datetime.now(),
            msg = res.get("msg")
        )
        db.session.add(gul)
        db.session.commit()
    except Exception as e:
        gul = GalaxyUploadLogs(
            creater=username,
            glm_ref=glm_obj.gal_ref,
            upload_type=type,
            lib_name=lib_name,
            task_name=foldername,
            msg = str(e)
        )
        db.session.add(gul)
        db.session.commit()




# 
# chunksize = 10485760
# 
# def getFileSize(file):  # 获取视频文件和切片文件大小\
#     file_all_size = os.path.getsize(file)  # 文件总大小
#     totalChunkCount = math.ceil(int(file_all_size) / chunksize)  # 文件切块数
#     lastchunkSize = file_all_size % chunksize  # 文件切块最后一块的大小
#     return file_all_size, totalChunkCount, lastchunkSize
# 
# def upload_progress(server_ip, headers, file_name, md5, file_all_size, chunkCount, dirId):
#     requrl = "http://{}/api/galaxy/v1/file/files:progress".format(server_ip)
#     data = [{
#         "fileMd5": md5,
#         "chunkCount": chunkCount,
#         "fileName": file_name,
#         "fileSize": file_all_size,
#         "dirId": dirId,
#         'parentId': dirId,
#         'totalChunks':chunkCount,
#     }]
#     r = requests.post(requrl, data=json.dumps(data), headers=headers)
#     result = r.json()
#     print(result ,123123213123123123123123)
# 
#     if result['data']:
#         uploadToken = result['data'][0]['fileId']
#     return uploadToken
# 
# 
# def upload_chunk(server_ip, headers, file_name, md5, file_all_size, totalChunkCount, uploadToken, index, chunk, chunksize,
#                  currentChunkSize):
#     requrl = "http://{}/api/galaxy/v1/file/files:create".format(server_ip)
#     files = {
#         'currentChunkIndex': str(index + 1),
#         'chunkSize': str(chunksize),
#         'currentChunkSize': str(currentChunkSize),
#         'fileSize': str(file_all_size),
#         'fileMd5': md5,
#         'fileName': file_name,
#         'fileId': uploadToken,
#         'totalChunkCount': str(totalChunkCount),
#         'file': (file_name, chunk, "video/vnd.dlna.mpeg-tts")
#         # 'file': (file_name, "chunk", "video/MP2T")
#     }
# 
#     m = MultipartEncoder(fields=files)
#     headers['Content-Type'] = m.content_type
# 
#     r = requests.post(requrl, headers=headers, data=m)
#     result = r.json()
#     headers['Content-Type'] = 'application/json;charset=UTF-8'
#     print(result)
#     if result['code'] == 0:
#         return True
#     else:
#         return False
# 
# 
# 
# 
# @celery.task
# def execute_upload_file_to_galaxy_folder(**kwargs):
#     server_ip = kwargs.get("server")
#     file_addr = kwargs.get("file_addr")
#     folder_id = kwargs.get("folder_id")
#     file_name = file_addr.split("/")[-1]
#     print(kwargs ,"asdasdasdasdas")
#     headers = {'Content-Type': 'application/json;charset=UTF-8',
#                "Module-Source": "video-structure-realtime-web",
#                'authorization': '59dacfac729esuperadmin427f90bfa98c0a636e0c'}
#     with open(file_addr,"rb") as f:
#         file = f.read()
#     file_md5= hashlib.md5(file).hexdigest()
#     (file_all_size, totalChunkCount, lastchunkSize) = getFileSize(file_addr)
#     print((file_all_size, totalChunkCount, lastchunkSize))
#     uploadToken = upload_progress(server_ip, headers, file_name, file_md5, file_all_size, totalChunkCount, folder_id)
#     with open(file_addr, "rb") as f:
#         index = 0
#         while True:
#             chunk = f.read(chunksize)
#             if (chunk):
#                 if index + 1 == totalChunkCount:
#                     currentChunkSize = lastchunkSize
#                 else:
#                     currentChunkSize = chunksize
#                 upload_chunk(server_ip, headers, file_name, file_md5, file_all_size, totalChunkCount, uploadToken, index, chunk,
#                              chunksize, currentChunkSize)
#                 index = index + 1
#             else:
#                 break

    # try:
    #     headers = {'Content-Type': 'application/json;charset=UTF-8',
    #                "Module-Source": "video-structure-realtime-web",
    #                'authorization': '59dacfac729esuperadmin427f90bfa98c0a636e0c'}
    #
    #     foldername = str(int(time.time() * 1000))
    #     requests.post("http://{}/api/galaxy/v1/album/task:checkName".format(server_ip) ,
    #                   data=json.dumps({"name": foldername}), headers=headers).json()
    #
    #     url =  "http://{}/api/galaxy/v1/album/task:photoUploadAnalyze".format(server_ip)
    #     files = {
    #         'file': (foldername, file, "video/vnd.dlna.mpeg-tts")
    #     }
    #     m = MultipartEncoder(fields=files)
    #     headers['Content-Type'] = m.content_type
    #     res = requests.post(url=url, data=m, headers=headers).json()
    #     print(res)
    #     headers['Content-Type'] = 'application/json;charset=UTF-8'
    #     # 生成任务
    #     url = "http://{}/api/galaxy/v1/album/task".format(server_ip)
    #     req = {
    #         "albumId": lib_id,
    #         "fileName": foldername,
    #         "fileTempPath": res["data"]["path"],
    #         "importType": "1",
    #         "rule": "root",
    #         "split": "_",
    #         "name": foldername,
    #         "uploadType": "PACKAGE",
    #     }
    #     if lib_type == "1":
    #         req["deployObject"] = 1
    #     elif  lib_type == "2":
    #         req["deployObject"] = 2
    #     elif  lib_type == "3":
    #         req["deployObject"] = 3
    #     else :
    #         req["deployObject"] = 5
    #
    #     res = requests.post(url=url, data=json.dumps(req), headers=headers).json()
    #     print(res)
    #     cmt_id = res.get("data").get( "cmtId")
    #     url =  "http://{}/zuul/api/galaxy/v1/album/task/photo/photoUpload:".format(server_ip) + cmt_id
    #     res = requests.post(url, headers=headers,
    #                         data=json.dumps({"cmtId": res.get("data").get("cmtId")})).json()
    #     print('上传底库成功：', res)
    #
    #     time.sleep(10)
    #     url =  "http://{}/api/galaxy/v1/album/task/".format(server_ip)+cmt_id
    #     res = requests.get(url=url, headers=headers).json()
    #     print(res)
    #
    #     for x in range(500):
    #         if res.get("data").get("status") == "FILE_NOT_UPLOAD":
    #             time.sleep(3)
    #         else:
    #             break
    #
    #
    #     gul = GalaxyUploadLogs(
    #         creater=username,
    #         glm_ref=glm_obj.gal_ref,
    #         upload_type=type,
    #         lib_name=lib_name,
    #         task_name=foldername,
    #         succeed_num = res.get("data").get("successTotal"),
    #         error_num= res.get("data").get("errTotal"),
    #         total_num= res.get("data").get("total"),
    #         start_at= datetime.datetime.utcfromtimestamp(int(str(res.get("data").get("createTime"))[:-3])),
    #         end_at=datetime.datetime.utcfromtimestamp(int(str(res.get("data").get("endTime"))[:-3])),
    #         msg = res.get("msg")
    #     )
    #     db.session.add(gul)
    #     db.session.commit()
    # except Exception as e:
    #     gul = GalaxyUploadLogs(
    #         creater=username,
    #         glm_ref=glm_obj.gal_ref,
    #         upload_type=type,
    #         lib_name=lib_name,
    #         task_name=foldername,
    #         msg = str(e)
    #     )
    #     db.session.add(gul)
    #     db.session.commit()
