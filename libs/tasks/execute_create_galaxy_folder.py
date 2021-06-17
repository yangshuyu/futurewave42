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



@celery.task
def execute_create_galaxy_folder(**kwargs):
    galaxy_server_ip = kwargs.get("server")
    dmp_addr = kwargs.get("dmp_addr")
    folder_name = kwargs.get("folder_name")
    folder_ids = kwargs.get("folder_id")
    username = kwargs.get("username")
    file_addr = kwargs.get("file_addr")
    parent_name = kwargs.get("parent_name")
    file_status = kwargs.pop("file_status")  #是否有文件上传

    if folder_ids:
        folder_f_id = folder_ids[-1]
    else:
        folder_f_id = "0"

    headers = {'Content-Type': 'application/json;charset=UTF-8',
               'authorization': '59dacfac729esuperadmin427f90bfa98c0a636e0c'}
    # 如果文件名称存在 就创建文件夹 再上传 否则就直接上传
    if folder_name:

        url = 'http://{}/api/galaxy/v1/file/files:folderCreate'.format(galaxy_server_ip)
        # 查询父级文件夹名称
        body = {"name": folder_name, "parentId": str(folder_f_id)}
        response = requests.post(url, data=json.dumps(body), headers=headers).json()
        id_url = 'http://{}/api/galaxy/v1/file/files'.format(galaxy_server_ip)
        id_res = {
            "dirId": '0',
            "fileName": folder_name,
            "pageNo": 1,
            "pageSize": 20,
            "status": 1,
        }
        id_response = requests.post(id_url, data=json.dumps(id_res), headers=headers).json()
        up_folder_id = id_response.get("data").get("records")[0].get("id")
    else:
        up_folder_id = folder_f_id

    if file_status :
        file_name =  file_addr.split("/")[-1]
        # 开始上传操作
        with open(file_addr, "rb") as f:
            file = f.read()
        file_md5 = hashlib.md5(file).hexdigest()
        (file_all_size, totalChunkCount, lastchunkSize) = getFileSize(file_addr)
        uploadToken = upload_progress(galaxy_server_ip, headers, file_name, file_md5, file_all_size, totalChunkCount, up_folder_id)
        with open(file_addr, "rb") as f:
            index = 0
            while True:
                chunk = f.read(chunksize)
                if (chunk):
                    if index + 1 == totalChunkCount:
                        currentChunkSize = lastchunkSize
                    else:
                        currentChunkSize = chunksize
                    upload_chunk(galaxy_server_ip, headers, file_name, file_md5, file_all_size, totalChunkCount, uploadToken,
                                 index, chunk, chunksize, currentChunkSize)
                    index = index + 1
                else:
                    break
    else:
        pass

    # 保存信息
    gf = GalaxyFolder(
        creater = username,
        folder_name = folder_name,
        folder_parent_name = parent_name,
        file_addr = dmp_addr,
        server = galaxy_server_ip,
        end_at = datetime.datetime.now(),
        status = "成功",
    )
    db.session.add(gf)
    db.session.commit()







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



