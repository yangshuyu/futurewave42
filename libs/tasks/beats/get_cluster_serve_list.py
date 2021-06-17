import datetime
import json
from ec import db, mongodb
import traceback
from ec.ext import celery
from ec.server.model import Server
import requests
from ec.node.model import Node
DevOps_Cookies = {
    'devops-login': "MTUxNzgwMTIyMXxtd0hteE1WdTF2Z0xuYXFMWW1UWXBOYUhhdFlrd0huYXhjTzE3OElLU1QybFM3M0lMempaVGpMVVFvU2pJTzFqYVRrbzVhWTRwbGJERDUyYWRBYUZKamZma0ttOGlOS3haUmdDcHc0LXM0RjZWRnRrQTlfR3ZQVW5keTMzTDZpSmZiN1E4dHAzYnRyYlUzVGJyTUFUMWxqYmRnUE84OHlZWlFzMk9fVENXbEZlcEsyZzNOYjV3WVJMQW85ZlFDSHU0dE1rUkdFdExoeGhzYnpjREpxdER5WnJpTkh6T3JNaS1PSXVmcWNIcmJtVGVsSnZDcEVEQ1NCT1lYVkUzQlU9fCAAxNV5iKIcX-vd6FIPD2yPQqJDub-vOL_FRuXZLvcc"
}

@celery.task(name="get_cluster_serve_list")
def get_cluster_serve_list():
    # 清理历史数据
    mongodb.db.serve_msg.drop()

    # 获取所有的master主机
    master_server = Server.query.filter(
        Server.id.in_(
            Node.query.filter(
                Node.master_id != None).with_entities(Node.server_id)
        )
    )
    for server_obj in master_server:
        print("**********************************************************************")
        server_json = {}
        server_json["devops_infra_password"] = ""
        server_json["server_id"] = server_obj.id
        server_json["ip"] = server_obj.ip
        server_json["username"] = server_obj.username
        server_json["server_type"] = server_obj.server_type
        server_json["password"] = server_obj.password
        server_json["hostname"] = server_obj.hostname
        server_json["serve_dict"] = {}
        server_json["serve_msg_created_at"] = str(datetime.datetime.now())
        try:
            url = 'http://{}:5432/api/v1/service?detail=1'.format(server_obj.ip)
            print(url)
            res_data = requests.get(url=url, cookies=DevOps_Cookies, timeout=2)
        except:
            print("该集群不可访问:{}".format(url))
            continue

        if res_data.status_code != 200:
            print("获取服务失败请重新获取 :{}".format(res_data.content))
            continue

        # 查询集群密码
        # "环境变量接口  http://10.122.100.225:5432/api/v1/cluster/env"
        try:
            pwd_res = requests.get("http://{}:5432/api/v1/cluster/env".format(server_obj.ip) , cookies=DevOps_Cookies, timeout=2)
            if pwd_res.status_code == 200:
                for y in pwd_res.json():
                    if y.get("k") == "DEVOPS_INFRA_PASSWORD":
                        server_json["devops_infra_password"] = y.get("v")
                        break
        except Exception as e:
            print(traceback.print_exc())
            print("get pwd api error ： {}".format(e))

        servers = res_data.json()

        serve_msg = []


        # 遍历所有的服务集
        for server in servers:

            # 获取名字的最后一个参数 来区分是什么服务  服务不同获取版本号方式不同 ( biz , core , gpdb)
            last_str = server.get('name', '').split('.')[-1]
            name_list = server.get('name', '').split('-')
            status = "succeed"
            try:
                for sub_serve in server.get("instances").keys():
                    if server.get("instances").get(sub_serve).get("state") != "running":
                        status = "error"
                        break
            except Exception as e:
                print(traceback.print_exc())
                status = "error"

            name_msg = {}
            if last_str == 'biz-biz':
                # 查询服务运行状态
                # 如果名字是10个 新的命名规则 ，如果是8个老的命名规则 ，其他做记录
                if len(name_list) == 10:
                    name_msg = {
                        "proId": name_list[0],
                        "verId": name_list[1],
                        "status":status,
                        "type": "biz",
                        "name_type": "new"
                    }
                    # server_json["serve_dict"] = name_msg
                    if name_msg not in serve_msg:
                        serve_msg.append(name_msg)
                elif len(name_list) == 8:
                    name_msg = {
                        "proId": name_list[4],
                        "verId": "",
                        "status": status,
                        "type": "biz",
                        "name_type": "old"
                    }
                    # server_json["serve_dict"] = name_msg
                    if name_msg not in serve_msg:
                        serve_msg.append(name_msg)
                else:
                    print("新的biz命名规则：名称--{}，url--{}".format(server.get('name', ''), url))

            elif last_str == 'core-core':
                # 获取 core版本号   # " core-core      ======     gateway-1"
                if "core-core" == last_str:
                    # "megvii.138-core-core.core-core.gateway-1"
                    key_name = "megvii." + server.get('name', '') + ".gateway-1"
                    try:
                        version = \
                            server.get("instances").get(key_name).get("monitor_container").get("Image").split(":")[
                                -1].split(
                                "-")[0]
                    except:
                        version = ""
                    name_msg = {
                        "proId": "core",
                        "status": status,
                        "verId": version,
                        "type": "core",
                    }
                    # server_json["serve_dict"] = name_msg
                    if name_msg not in serve_msg:
                        serve_msg.append(name_msg)

            elif last_str.split('-')[0] == 'gpdb':
                name_msg = {
                    "proId": "gpdb",
                    "verId": "",
                    "status": status,
                    "type": "gpdb",
                }
                # server_json["serve_dict"] = name_msg
                if name_msg not in serve_msg:
                    serve_msg.append(name_msg)
            else:
                # 处理特殊的biz
                if last_str.split("-")[0] == 'biz':
                    # 判断该服务有没有biz-biz服务
                    sm_status = False
                    for sm in serve_msg:
                        if len(name_list) == 10:
                            if sm.get("proId")  ==  name_list[0] :
                                sm_status = True
                                break
                        else:
                            try:
                                if sm.get("proId") == name_list[4]:
                                    sm_status = True
                                    break
                            except:
                                break
                    if not sm_status:
                        if len(name_list) == 10:
                            name_msg = {
                                "proId": name_list[0],
                                "verId": name_list[1],
                                "status": status,
                                "type": "biz",
                                "name_type": "new"
                            }
                            if name_msg not in serve_msg:
                                serve_msg.append(name_msg)
                        elif len(name_list) == 8:
                            name_msg = {
                                "proId": name_list[4],
                                "verId": "",
                                "status": status,
                                "type": "biz",
                                "name_type": "old"
                            }
                            if name_msg not in serve_msg:
                                serve_msg.append(name_msg)
                    pass
                # print("新的服务命名规则：名称--{}，url--{}".format(server.get('name', ''), url))
        # 收集服务包含的服务信息结束  拿mongo服务信息进行匹配并保存
        for x in serve_msg:
            server_json.pop("_id",None)
            if x.get("name_type") == "old":
                # 老名字保存
                res = mongodb.db.b_p_pro_ver.find_one({"proId": x.get("proId")})
                if res:
                    x["pro_ver_ref"] = res.get("_id")
                    x["pro_ref"] = res.get("pro_ref")
                    x["product"] = res.get("product")
                    x["version"] = ""

                if x.get("pro_ref"):
                    # 如果和天狼有关联 组装天狼信息
                    ec_res = mongodb.db.product.find_one({"_id": x.get("pro_ref"), "isDeleted": None})
                    # x["ec_version"] = ec_res.get("version")
                    x["ec_product"] = ec_res.get("product")
                    x["ec_id"] = ec_res.get("ec_id")
            else:
                res = mongodb.db.b_p_pro_ver.find_one({"proId": x.get("proId")})
                if res:
                    x["pro_ver_ref"] = res.get("_id")
                    x["pro_ref"] = res.get("pro_ref")
                    x["product"] = res.get("product")
                    x["version"] = ""
                if x.get("pro_ref"):
                    # 如果和天狼有关联 组装天狼信息
                    ec_res = mongodb.db.product.find_one({"_id": x.get("pro_ref"), "isDeleted": None})
                    # x["ec_version"] = ec_res.get("version")
                    x["ec_product"] = ec_res.get("product")
                    x["ec_id"] = ec_res.get("ec_id")
                # 新名字保存
                res = mongodb.db.b_p_pro_ver.find_one({"proId": x.get("proId"),"verId":x.get("verId")})
                if res:
                    x["pro_ver_ref"] = res.get("_id")
                    x["pro_ref"] = res.get("pro_ref")
                    x["product"] = res.get("product")
                    x["version"] = res.get("version")
                if x.get("pro_ref"):
                    # 如果和天狼有关联 组装天狼信息
                    ec_res = mongodb.db.product.find_one({"_id": x.get("pro_ref"), "isDeleted": None})
                    x["ec_version"] = ec_res.get("version")
                    x["ec_product"] = ec_res.get("product")
                    x["ec_id"] = ec_res.get("ec_id")
            server_json["serve_dict"] = x
            mongodb.db.serve_msg.save(server_json)



