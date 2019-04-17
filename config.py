# edit the URI below to add your RDS password and your AWS URL
# The other elements are the same as used in the tutorial
# format: (user):(password)@(db_identifier).amazonaws.com:3306/(db_name)


# Uncomment the line below to work with AWS DB
# SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://smileyface:cs411project@rds-mysql-411project.csfttfyvdoqe.us-east-1.rds.amazonaws.com/project'

# Uncomment the line below to work with a local DB
SQLALCHEMY_DATABASE_URI = 'sqlite:///test.db'

SQLALCHEMY_POOL_RECYCLE = 3600
SQLALCHEMY_TRACK_MODIFICATIONS = False
WTF_CSRF_ENABLED = True
# SECRET_KEY = 'dsaf0897sfdg45sfdgfdsaqzdf98sdf0a'
