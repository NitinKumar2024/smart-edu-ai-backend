import pymysql


# for server
def get_db_connection():
    return pymysql.connect(
        host='localhost',
        user='smart-edu-ai-flask',
        password='OU1vT26p3uAiGd3vvymt',
        database='smart-edu-ai-flask'
    )

# def get_db_connection():
#     return pymysql.connect(
#         host='host.docker.internal',
#         user='root',
#         password='',
#         database='smart-edu-ai-flask'
#     )
