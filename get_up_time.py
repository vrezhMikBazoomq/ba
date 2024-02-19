import pandas as pd
from sqlalchemy import create_engine
file_path = '___beacon.csv'

df = pd.read_csv(file_path)

selected_columns = ['date', 'Name', 'uint32__upTime']

df = df[selected_columns]

df = df.dropna(subset=['uint32__upTime'])

mysql_credentials = {
    'username': 'root',
    'password': 'root',
    'host': 'localhost',
    'database': 'beacon',
}

connection_string = f'mysql+mysqlconnector://{mysql_credentials["username"]}:{mysql_credentials["password"]}@{mysql_credentials["host"]}/{mysql_credentials["database"]}'

engine = create_engine(connection_string)

table_name = 'uptime'

df.to_sql(name=table_name, con=engine, if_exists='replace', index=False)


