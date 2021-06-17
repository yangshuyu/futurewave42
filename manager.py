from flask_migrate import MigrateCommand
from flask_script import Manager

from futurewave42.app import create_app
from futurewave42.account.model import User
from futurewave42.configuration.model import Configuration

manager = Manager(create_app)
manager.add_command('db', MigrateCommand)


if __name__ == '__main__':
    manager.run()
