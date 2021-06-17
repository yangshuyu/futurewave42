from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


class ReportDb():
    def __init__(self):
        engine = create_engine('mysql://automation:automation@10.199.0.45:3306/report_debug')
        self.session = sessionmaker(bind=engine)


