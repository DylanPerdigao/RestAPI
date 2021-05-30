# imports
from re import A
from flask import Flask, request, jsonify
import datetime
import jwt
from functools import wraps
import platform
import os
import random
# custom modules
import modules.Database as database
import modules.Utils as utils

# config
global db
app = Flask(__name__)


def encode_auth_token(user_id):
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


def decode_auth_token(f):
    """
    Decodes the auth token

    :param f:

    :return: integer|string
    """

    @wraps(f)  # why? -> https://www.geeksforgeeks.org/python-functools-wraps-function/
    def inner(*args, **kwargs):

        if 'Token' not in request.headers or not request.headers['Token']:
            return jsonify({'erro': 401, 'message': 'Token is missing!!!'})

        authToken = request.headers['Token']

        try:
            payload = jwt.decode(
                authToken,
                b'\x13\xfc\xe2\x92\x0eE4\xd2\x92\xdd\xd4\x11np\xc8\x0c+<\xb1\xe8i\xf0\xc4O',
                algorithms=['HS256']
            )
            username = payload['sub']
        except jwt.ExpiredSignatureError:
            return jsonify({'erro': 401, 'message': 'Signature expired. Please log in again.'})

        except jwt.InvalidTokenError:
            return jsonify({'erro': 401, 'message': 'Invalid token. Please log in again.'})

        return f(username, *args, **kwargs)

    return inner


@app.route('/dbproj/user', methods=['POST'])
def signUp():
    """
    Registar um utilizador

    :return: resposta da request
    """
    id = None
    try:
        content = request.json
        valid = utils.validateTypes(content, [str, str, str])
        valid = valid & utils.isemail(content['email'])
        if not valid:
            return jsonify({'erro': 404})
        id = db.signUp(content['username'], content['email'], content['password'])
    except Exception as e:
        db.connection.rollback()
        print(e)
        return jsonify({'erro': 401})
    print(f"Added user #{id}")
    return jsonify({'userId': id})


@app.route('/dbproj/user', methods=['PUT'])
def signIn():
    """Login do utilizador"""
    try:
        content = request.json
        valid = utils.validateTypes(content, [str, str])
        if not valid:
            return jsonify({'erro': 404})
        correctSignIn = db.signIn(content['username'], content['password'])
        if correctSignIn == True:
            token = encode_auth_token(content['username'])

            return jsonify({'authToken': token})

        # Is Banned
        elif 'banned' == correctSignIn:
            return jsonify({'erro': 'User is banned'})
        # wrong credentials
        return jsonify({'erro': 401, 'message': 'Wrong credentials'})

    except Exception as e:
        print(e)
        return jsonify({'erro': 401, 'message': e})


@app.route('/dbproj/leilao', methods=['POST'])
@decode_auth_token
def createAuction(username):
    """Criar Leilão"""
    id = None
    try:
        content = request.json
        valid = utils.validateTypes([username], [str])
        valid = valid & utils.validateTypes(content, [int, float, str, str, str, str])
        valid = valid & utils.validateDates([content['dataInicio'], content['dataFim']])
        if not valid:
            return jsonify({'erro': 404})
        id = db.createAuction(username, content['artigoId'], content['precoMinimo'], content['dataInicio'],
                              content['dataFim'], content['titulo'], content['descricao'])
    except Exception as e:
        db.connection.rollback()
        print(e)
        return jsonify({'erro': 401})
    print(f"Added auction #{id}")
    return jsonify({'leilãoId': id})


@app.route('/dbproj/leiloes', methods=['GET'])
@decode_auth_token
def listAllAuctions(username):
    """Listar Todos os leilões existentes"""
    try:
        auctions = db.listAllAuctions()
    except Exception as e:
        print(e)
        return jsonify({'erro': 401})
    return jsonify(auctions)


@app.route('/dbproj/leiloes/<keyword>', methods=['GET'])
@decode_auth_token
def listCurrentAuctionsByKeyword(username, keyword):
    """Listar os leilões que estão a decorrer"""
    try:
        valid = utils.validateTypes([keyword], [str])
        if not valid:
            return jsonify({'erro': 404})
        auctions = db.listAuctions(keyword)
    except Exception as e:
        print(e)
        return jsonify({'erro': 401})
    return jsonify(auctions)


@app.route(f'/dbproj/user/leiloes', methods=['GET'])
@decode_auth_token
def listUserAuctions(username):
    """Listar os leilões em que o utilizador tenha uma atividade"""
    try:
        valid = utils.validateTypes([username], [str])
        if not valid:
            return jsonify({'erro': 404})
        auctions = db.listUserAuctions(username)
    except Exception as e:
        db.connection.rollback()
        print(e)
        return jsonify({'erro': 401})
    return jsonify(auctions)  # TODO ajeitar isto


@app.route(f'/dbproj/licitar/<leilaoId>/<licictacao>', methods=['POST'])  # TODO leilaoId
@decode_auth_token
def bid(username, leilaoId, licictacao):
    """Listar os leilões em que o utilizador tenha uma atividade"""
    try:
        valid = utils.validateTypes([username, leilaoId, licictacao], [str, int, float])
        if not valid:
            return jsonify({'erro': 404})
        bid_id = db.bid(username, leilaoId, licictacao)
        if bid_id == 'inactive':
            return jsonify({'erro': 'O leilão está inativo'})
    except Exception as e:
        print(e)
        return jsonify({'erro': 401})
    return jsonify({'licitacaoId': bid_id})


@app.route('/dbproj/leilao/<leilaoId>', methods=['GET'])
@decode_auth_token
def detailsAuction(username, leilaoId):
    """Consultar os detalhes de um determinado leilão"""
    try:
        valid = utils.validateTypes([leilaoId], [int])
        if not valid:
            return jsonify({'erro': 404})
        details = db.detailsAuction(leilaoId)
    except Exception as e:
        print(e)
        return jsonify({'erro': 401})
    return jsonify(details)


@app.route('/dbproj/feed/<leilaoId>', methods=['POST'])
@decode_auth_token
def writeFeedMessage(username, leilaoId):
    """Escrever mensagem no mural de um leilão"""
    try:
        content = request.json
        print(content)
        valid = utils.validateTypes([username, leilaoId], [str, int])
        valid = valid & utils.validateTypes(content, [str, str])
        if not valid:
            return jsonify({'erro': 404})
        message_id = db.writeFeedMessage(username, leilaoId, content["message"], content["type"])
    except Exception as e:
        print(e)
        return jsonify({'erro': 401})
    return jsonify({'messageId': message_id})


@app.route('/dbproj/leilao/edit/<leilaoId>', methods=['PUT'])
@decode_auth_token
def editAuction(username, leilaoId):
    """Editar propriedades de um leilão"""
    try:
        content = request.json
        valid = utils.validateTypes([username, leilaoId], [str, int])
        valid = valid & utils.validateTypes(content, [str, str])
        if not valid:
            return jsonify({'erro': 404})
        res = db.editAuction(leilaoId, content["titulo"], content["descricao"], username)
        if res == "notCreator":
            return jsonify({'erro': "User is not the auction's creator"})
        # Error on insert
        elif not res:
            return jsonify({'erro': 401})
        return jsonify(res)
    except Exception as e:
        print(e)
        return jsonify({'erro': 401})


@app.route('/dbproj/leilao/checkFinish', methods=['PUT'])
@decode_auth_token
def finishAuction(username):
    """Terminar leilão na data, hora e minuto marcados"""
    try:
        db.finishAuctions()
    except Exception as e:
        print(e)
        return jsonify({'erro': 401})


@app.route('/dbproj/ban/<user>', methods=['PUT'])
@decode_auth_token
def ban(username, user):
    """Banir um utilizador definitivamente"""
    try:
        valid = utils.validateTypes([username, user], [str, str])
        if not valid:
            return jsonify({'erro': 404})
        admin_id, user_id = db.ban(username, user)
    except Exception as e:
        db.connection.rollback()
        print(e)
        return jsonify({'erro': 401})
    return jsonify({'adminId': admin_id, 'userId': user_id})


@app.route('/dbproj/leilao/cancel/<leilaoId>', methods=['PUT'])
@decode_auth_token
def cancelAuction(username, leilaoId):
    """Um administrador pode cancelar um leilão"""
    try:
        valid = utils.validateTypes([username, leilaoId], [str, int])
        if not valid:
            return jsonify({'erro': 404})
        res = db.cancelAuction(leilaoId, username)
        db.connection.commit()
        if res == "notAdmin":
            return jsonify({'erro': "Sem permissões de administrador!"})
        elif res == "noAuction":
            return jsonify({'erro': "O leilão não existe!"})
        elif res == "inactive":
            return jsonify({'erro': "O leilão já está cancelado!"})
        else:
            return jsonify(res)
    except Exception as e:
        db.connection.rollback()
        print(e)
        return jsonify({'erro': 401})


@app.route('/')
@app.route('/home')
def home():
    return "<h1><center>BidYourAuction<center></h1>"


if __name__ == '__main__':
    '''
    BIDYOURAUCTION_USER = os.environ.get('BIDYOURAUCTION_USER')
    BIDYOURAUCTION_PASSWORD = os.environ.get('BIDYOURAUCTION_PASSWORD')
    BIDYOURAUCTION_HOST = os.environ.get('BIDYOURAUCTION_HOST')
    BIDYOURAUCTION_PORT = os.environ.get('BIDYOURAUCTION_PORT')
    BIDYOURAUCTION_DB = os.environ.get('BIDYOURAUCTION_DB')
    '''

    BIDYOURAUCTION_HOST = "ec2-34-254-69-72.eu-west-1.compute.amazonaws.com"
    BIDYOURAUCTION_PORT = "5432"
    BIDYOURAUCTION_DB = "das7ket3c5aarn"
    BIDYOURAUCTION_PASSWORD = "eb4ada6829ffce0e0f516062ea258ca6aa14d2fd85ea907ad910aa62eaf1412a"
    BIDYOURAUCTION_USER = "vtxuzrplfviiht"

    print(BIDYOURAUCTION_USER, BIDYOURAUCTION_PASSWORD, BIDYOURAUCTION_HOST, BIDYOURAUCTION_PORT, BIDYOURAUCTION_DB)
    db = database.Database(
        user=BIDYOURAUCTION_USER,
        password=BIDYOURAUCTION_PASSWORD,
        host=BIDYOURAUCTION_HOST,
        port=BIDYOURAUCTION_PORT,
        database=BIDYOURAUCTION_DB
    )
    app.run(debug=True, host='localhost', port=8080)
