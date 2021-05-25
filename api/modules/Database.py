import datetime

import psycopg2
import jwt


class Database(object):
    def __init__(self, user, password, host, port, database):
        self.user = user
        self.password = password
        self.host = host
        self.port = port
        self.database = database
        self.connect()

    def connect(self):
        self.connection = psycopg2.connect(
            user=self.user,
            password=self.password,
            host=self.host,
            port=self.port,
            database=self.database
        )


    def insert(self, sql, return_sql=None):
        """ Insere na base de dados"""
        cursor = self.connection.cursor()
        cursor.execute(sql)
        self.connection.commit()
        if(return_sql!=None):
            cursor.execute(return_sql)
        res = cursor.fetchone()[0]
        cursor.close()
        return res

    def selectOne(self, sql):
        """ Seleciona na base de dados"""
        cursor = self.connection.cursor()
        cursor.execute(sql)
        res = cursor.fetchone()[0]
        cursor.close()
        return res

    def selectAll(self,sql):
        """ Seleciona na base de dados"""
        cursor = self.connection.cursor()
        cursor.execute(sql)
        res = cursor.fetchall()
        cursor.close()
        return res

    def remove(self, sql):
        pass

    def update(self, sql):
        pass

    def print(self):
        print("user = ", self.user)
        print("password = ", self.password)
        print("host = ", self.host)
        print("port = ", self.port)
        print("database = ", self.database)

    def signIn(self, username, password):
        cursor = self.connection.cursor()
        cursor.execute(f"""
        SELECT * FROM participant WHERE person_username = '{username}' AND person_password = '{password}'""")
        if cursor.rowcount < 1:
            return 'AuthError'
        cursor.close()
        return self.encode_auth_token(username)

    def encode_auth_token(self, user_id):
        """
        Generates the Auth Token
        :return: string
        """
        try:
            payload = {
                'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=1),
                'iat': datetime.datetime.utcnow(),
                'sub': user_id
            }
            return jwt.encode(
                payload,
                b'\x13\xfc\xe2\x92\x0eE4\xd2\x92\xdd\xd4\x11np\xc8\x0c+<\xb1\xe8i\xf0\xc4O',
                algorithm='HS256'
            )
        except Exception as e:
            return e

    @staticmethod
    def decode_auth_token(auth_token):
        """
        Decodes the auth token
        :param auth_token:
        :return: integer|string
        """
        try:
            payload = jwt.decode(auth_token,
                                 b'\x13\xfc\xe2\x92\x0eE4\xd2\x92\xdd\xd4\x11np\xc8\x0c+<\xb1\xe8i\xf0\xc4O')
            return payload['sub']
        except jwt.ExpiredSignatureError:
            return 'Signature expired. Please log in again.'

        except jwt.InvalidTokenError:
            return 'Invalid token. Please log in again.'

    def listAuctions(self, param):
        cursor = self.connection.cursor()
        sql = f"""SELECT id, description FROM auction, textual_description WHERE auction.id = textual_description.auction_id AND (auction.code::text = '{param}' OR textual_description.description like '%{param}%')"""
        cursor.execute(sql)
        if cursor.rowcount < 1:
            res = []
        else:
            res = [{"leilaoId": row[0], "descricao": row[1]} for row in cursor.fetchall()]
        cursor.close()
        return res


if __name__ == '__main__':
    # testar codigo desta classe aqui
    db = Database("bidyourauction", "bidyourauction", "docker.for.mac.localhost", "5432", "bidyourauction_db")
    db.print()
