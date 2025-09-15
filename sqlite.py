import sqlite3

connection=sqlite3.connect('student.db')

cursor=connection.cursor()

table_info="""
create table STUDENT(NAME VARCHAR(20),CLASS VARCHAR(25),SECTION VARCHAR(25),MARKS INT);
"""
cursor.execute(table_info)

cursor.execute('''insert into STUDENT values('John','Data Science','A',85)''')
cursor.execute('''insert into STUDENT values('Doe','Data Science','B',90)''')
cursor.execute('''insert into STUDENT values('Smith','Data Science','A',78)''')
cursor.execute('''insert into STUDENT values('Jane','DevOps','C',88)''')
cursor.execute('''insert into STUDENT values('Emily','DevOps','B',92)''')

print("Inserted data are")
data=cursor.execute('''select * from STUDENT''')
for row in data:
    print(row)

connection.commit()
connection.close()