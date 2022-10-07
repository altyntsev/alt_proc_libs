import re

import databases
from IPython.terminal.debugger import set_trace as bp
from pprint import pprint

class DB:

    def __init__(self, host='127.0.0.1', port=5432, user=None, pwd=None, db=None):
        self.connection_url = f'postgresql://{user}:{pwd}@{host}:{port}/{db}'
        self.db = databases.Database(self.connection_url)

    async def connect(self):
        await self.db.connect()

    async def find(self, row_class, sql, params=None):
        rows = await self.query(sql, params)
        res = []
        for row in rows:
            res.append(row_class(**row))
        return res

    async def find_one(self, row_class, sql, params=None):
        res = await self.find(row_class, sql, params)
        if not res:
            return None
        if len(res) > 1:
            raise Exception('Not one found')
        return res[0]

    async def query(self, sql, params=None):
        if params and not isinstance(params, dict):
            params = params.dict()
        value_attrs = re.findall(':([\w_]*)', sql)
        values = {attr: params[attr] for attr in value_attrs}
        # print(sql, values)
        rows = await self.db.fetch_all(sql, values)
        rows = [dict(row.items()) for row in rows]

        return rows

    async def execute(self, sql, params=None):
        res = await self.db.execute(sql, params)

        return res

    async def insert(self, sql, params, id_field=None):
        if params and not isinstance(params, dict):
            params = params.dict()
        if id_field:
            sql += f' returning {id_field}'
        value_attrs = re.findall(':([\w_]*)', sql)
        values = {attr: params[attr] for attr in value_attrs}
        res = await self.db.execute(sql, values)

        return res


