import datetime
import pymysql
import time
import json,requests
from ec.ext import db
import paramiko
import random,string
from ec.server.model import UserServe, Server
from random import randint
from ec.galaxy_tool.model import AuthDataRecord,CameraDataRecord,GB_Camera
from flask_mail import Message

from ec.ext import celery, mail
@celery.task
def insert_authdata(**args):
    adddata={"creater":args.get("creater"),"data_type":args.get("type"),"data_num":args.get("num"),"data_name":args.get("dataname"),"db_host":args.get("dbdata").get("host"),"status":"进行中","detail":args.get("parent_dpt")}
    record=AuthDataRecord.add(**adddata)
    try:
        conn = pymysql.connect(host=args["dbdata"]["host"], port=int(args["dbdata"]["port"]), db="auth2",
                               user=args["dbdata"]["username"],
                               password=args["dbdata"]["passwd"], charset="utf8", write_timeout=10)
        cur = conn.cursor()

        if args["type"] == "dpt":
            cur.execute('select num from auth_organization where id="' + args["parent_dpt"] + '"')
            parent_dpt_num = cur.fetchall()[0][0]
            cur.execute('select org_level from auth_organization where id="' + args["parent_dpt"] + '"')
            parent_org_level = cur.fetchall()[0][0]
            cur.execute('select max(num) from auth_organization')
            max_num = cur.fetchall()[0][0]
            sqlargs = []
            for i in range(1, int(args["num"]) + 1):
                random_id = "0c01e8eb-78c5-47c7-be7d-" + "".join(
                    random.sample(string.ascii_letters + string.digits, 12))
                sqlargs.append((random_id, args["dataname"] + str(i), args["parent_dpt"],str(int(parent_org_level)+1), str(int(max_num + i)),
                                str(parent_dpt_num) + "_" + str(int(max_num + i))))

            sql = "insert into auth_organization (id,org_name,parent_id,org_level,hidden,num,parents_pattern,creator_id,modifier_id,is_deleted,order_code) values(%s,%s,%s,%s,0,%s,%s,'73d82f01-dc1e-4666-bc79-3e59fc574cee','73d82f01-dc1e-4666-bc79-3e59fc574cee',0,26)"

            a = 1
            cur.executemany(sql, sqlargs)
            conn.commit()

        if args["type"] == "role":
            sqlargs = []
            for i in range(1, int(args["num"]) + 1):
                random_id = "0c01e8eb-78c5-47c7-be7d-" + "".join(
                    random.sample(string.ascii_letters + string.digits, 12))
                sqlargs.append((random_id, args["dataname"] + str(i)))

            sql = "insert into auth_role (id,name,hidden,,is_deleted) values(%s,%s,0,0)"
            cur.executemany(sql, sqlargs)
            conn.commit()
        #添加用户，调用中台api
        if args["type"] == "user":
            sqlargs = []
            #超级token
            token="59dacfac729esuperadmin427f90bfa98c0a636e0c"
            token="PYBZpqBVFrtpdjebzODNMCNPfRYFoAUiPRfMiXRzNgbJeZgccFcMiTdMVmDo"
            url="http://"+args["dbdata"]["host"]+"/api/galaxy/v1/auth/users"
            headers = {
                'Authorization': token,
                "Content-Type": "application/json;charset=UTF-8",
            }
            success_num=0
            for i in range(1, int(args["num"]) + 1):
                random_id = "0c01e8eb-78c5-47c7-be7d-" + "".join(
                    random.sample(string.ascii_letters + string.digits, 12))
                sqlargs.append((random_id, args["dataname"] + str(i)))
                data = json.dumps({
                    "userName": args["dataname"],
                    "userPwd": args["passwd"],
                    "pkiId": "",
                    "userRealName": args["dataname"] + str(i),
                    "phoneNo": "",
                    "employeeId": "",
                    "organizationId": args["auth_dpt"],
                    "email": None,
                    "userPortraitPath": "null",
                    "thumb": "/static/img/history_avatar.e385b.svg",
                    "enabled": "null",
                    "roleIds": [
                        args["auth_role"]
                    ],
                    "datas": {
                        "key1": "null",
                        "key2": "null"
                    },
                    "hidden": "null",
                    "ip": "",
                    "sso": "null"
                })
                r = requests.post(url, headers=headers, data=data, cookies=None, timeout=30)
                rr = r.json()
                if rr["msg"]=="成功":
                    success_num+=1

            # sql = "insert into auth_user (id,username,parent_id,org_level,hidden,num,parents_pattern,creator_id,modifier_id,is_deleted,order_code) values(%s,%s,%s,2,0,%s,%s,'73d82f01-dc1e-4666-bc79-3e59fc574cee','73d82f01-dc1e-4666-bc79-3e59fc574cee',0,26)"
            # cur.executemany(sql, sqlargs)
            # conn.commit()
    except Exception as e:
        record.update(**({"status": "失败"}))
        return {'code': 0, 'msg': "数据创建异常" + e, "data": []}
    record.update(**({"status":"完成"}))
    return {'code': 0, 'msg': "数据创建成功", "data": []}

@celery.task
def insert_authdata_sql(**args):
    adddata={"creater":args.get("creater"),"data_type":"sql","data_num":args.get("num"),"data_name":"自定义","db_host":args.get("dbdata").get("host"),"status":"进行中","detail":args.get("sql")}
    record=AuthDataRecord.add(**adddata)
    try:
        conn = pymysql.connect(host=args["dbdata"]["host"], port=int(args["dbdata"]["port"]), db="auth2",
                               user=args["dbdata"]["username"],
                               password=args["dbdata"]["passwd"], charset="utf8", write_timeout=10)
        cur = conn.cursor()
        sqlargs = []
        for i in range(1, int(args["num"]) + 1):
            sqlargs.append(())

        sql =args.get("sql")
        cur.executemany(sql, sqlargs)
        conn.commit()
    except Exception as e:
        record.update(**({"status": "失败"}))
        return {'code': 0, 'msg': "数据创建异常" + e, "data": []}
    record.update(**({"status":"完成"}))
    return {'code': 0, 'msg': "数据创建成功", "data": []}


@celery.task
def insert_videocamera(**args):

    token = "59dacfac729esuperadmin427f90bfa98c0a636e0c"
    headers = {
        'Authorization': token,
        "Content-Type": "application/json;charset=UTF-8",
    }
    dataname=args.get("dataname")
    CB_version = args.get("CB_version")
    bayonetType =args.get("bayonetType")
    dpt = args.get("dpt")
    cloudbridge_host = args.get("host")
    protocol_type= args.get("protocol_type")
    cameras = args.get("cameras")
    camera_type=args.get("camera_type")
    adddata = {"creater": args.get("creater"), "camera_type": args.get("camera_type"), "data_num": len(cameras),
               "pre_name": dataname, "server_ip": cloudbridge_host, "status": "进行中",
               "detail": ""}
    record = CameraDataRecord.add(**adddata)
    success_num=0
    try:
        #视频流相机创建
        if camera_type=="video":
            for camera_url in cameras:
                # 云桥创建
                random_name = "".join(
                    random.sample(string.ascii_letters + string.digits, 4))
                data = {
                    "name": dataname+random_name,
                    "type": "1",
                    "manufacturer": protocol_type,
                    "deptName": "总部",
                    "deptId": dpt,
                    "url": camera_url,
                    "closed": False,
                    "shareModel": "0",
                    "statusSyncInterval": "5",
                    "face": True,
                    "faceTTL": 90,
                    "full": False,
                    "fullTTL": 7,
                    "lowQuality": False,
                    "vface": True,
                    "vfaceTTL": 90,
                    "vfull": False,
                    "vfullTTL": 7,
                    "vlowQuality": False,
                    "lat": float("39."+str(randint(1,999999))),
                    "lon": float("116."+str(randint(1,999999))),
                    "ptz": False,
                    "ipAddr": str(randint(1,254))+"."+str(randint(1,254))+"."+str(randint(1,254))+"."+str(randint(1,254)),
                    "cmdPort": "3000",
                    "videoPort": 554,
                    "username": "admin",
                    "password": "admin123",
                    "bayonetType": bayonetType,
                    "active": False,
                    "recordType": 1,
                    "period": 35,
                    "alarmClip": False,
                    "tagCodes": [
                        "1000012"
                    ]
                }
                url = "http://"+cloudbridge_host+"/api/rainbow/v1/device/cameras"
                r = requests.post(url, headers=headers, data=json.dumps(data))
                rr = r.json()
                if rr["msg"]=="成功":
                    success_num+=1
        if camera_type=="kafka":
            for camera_url in cameras:
                # 云桥创建
                random_name = "".join(
                    random.sample(string.ascii_letters + string.digits, 4))
                data = {
                    "name": dataname+random_name,
                    "type": "15",
                    "manufacturer": protocol_type,
                    "deptName": "总部",
                    "deptId": dpt,
                    "url": camera_url,
                    "closed": False,
                    "shareModel": "0",
                    "statusSyncInterval": "5",
                    "face": True,
                    "faceTTL": 90,
                    "full": False,
                    "fullTTL": 7,
                    "lowQuality": False,
                    "vface": True,
                    "vfaceTTL": 90,
                    "vfull": False,
                    "vfullTTL": 7,
                    "vlowQuality": False,
                    "lat": float("39."+str(randint(1,999999))),
                    "lon": float("116."+str(randint(1,999999))),
                    "ptz": False,
                    "username": "admin",
                    "password": "admin123",
                    "videoPort": 554,
                    "bayonetType": bayonetType,
                    "active": False,
                    "recordType": 1,
                    "period": 35,
                    "alarmClip": False,
                    "tagCodes": [
                        "1000012"
                    ]
                }
                url = "http://"+cloudbridge_host+"/api/rainbow/v1/device/cameras"
                r = requests.post(url, headers=headers, data=json.dumps(data))
                rr = r.json()

                if rr["msg"]=="成功":
                    success_num+=1
    except Exception as e:
        record.update(**({"status": "失败"}))
        return {'code': 0, 'msg': "数据创建异常" + e, "data": []}
    if success_num==len(cameras):
        record.update(**({"status":"完成"}))
    elif success_num==0:
        record.update(**({"status": "失败"}))
    else:
        record.update(**({"status": "部分完成","detail":"成功："+str(success_num)}))
    return {'code': 0, 'msg': "数据创建成功", "data": []}

#gb相机创建
@celery.task
def create_gbcamera(**args):

    server_id=args.get("server_id")
    upper_ip=args.get("upper_ip")
    CivilCodeNum=args.get("CivilCodeNum")
    DeviceNum=args.get("DeviceNum")
    operater=args.get("operater")
    local_id=""
    after_name=args.get("after_name")
    local_port=args.get("local_port")
    iot_port=args.get("iot_port")
    gb_server = GB_Camera.get_gbcamera_by_server_id(server_id)
    server = Server.find_by_id(server_id)
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(
        hostname=server.ip,
        username=server.username,
        password=server.password
    )

    try:
        cmd='sudo sh /mnt/data/gb_lite_linux/start.sh '+ str(CivilCodeNum-1)+' '+str(DeviceNum-2)+' '+server.ip+' '+upper_ip+' '+after_name+' '+local_port+' '+iot_port
        stdin, stdout, stderr = client.exec_command(cmd, get_pty=True)
        stdin.write('%s\n' % server.password)
        for s in stdout.read().decode('utf-8').split('\n'):
            print(s)
            if "local_id" in s:
                local_id=s.split(":")[1].split("\r")[0]
                gb_server.update(**(
                {"local_id": local_id, "operater": operater, "CivilCodeNum": CivilCodeNum, "DeviceNum": DeviceNum,
                 "upper_ip": upper_ip}))

        client.close()

    except Exception as e:
        print(e)
    return {'code': 0, 'msg': "数据创建成功", "data": []}
