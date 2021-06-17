from ec.ext import celery


@celery.task
def test(**kwargs):
    pass
