from ec.bpmanage.models import Product
from ec.testcenter.models import Product as Product2
from ec.ext import celery


@celery.task(name='bp_product_synchronize')
def bp_product_synchronize():
    # 编排管理跟主系统进行同步
    Product.sync_project()
    # 同步接口自动化的产品和版本
    Product2.sync_project()

