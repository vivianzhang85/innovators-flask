from flask import Blueprint, jsonify
from flask_restful import Api, Resource
import requests
import random
from hacks.lyrics import *

lyric_api = Blueprint('lyric_api', __name__, url_prefix='/api/lyrics')
api = Api(lyric_api)

class LyricsAPI:
    # not implemented
    class _Create(Resource):
        def post(self, lyric):
            pass

    # getLyrics()
    class _Read(Resource):
        def get(self):
            return jsonify(getLyrics())

    # getLyric(id)
    class _ReadID(Resource):
        def get(self, id):
            return jsonify(getLyric(id))

    # getRandomLyric()
    class _ReadRandom(Resource):
        def get(self):
            return jsonify(getRandomLyric())

    # countLyrics()
    class _ReadCount(Resource):
        def get(self):
            count = countLyrics()
            countMsg = {'count': count}
            return jsonify(countMsg)

    # put method: addLyricLove
    class _UpdateLove(Resource):
        def put(self, id):
            addLyricLove(id)
            return jsonify(getLyric(id))

    # put method: addLyricDislike
    class _UpdateDislike(Resource):
        def put(self, id):
            addLyricDislike(id)
            return jsonify(getLyric(id))

# building RESTapi resources/interfaces, these routes are added to Web Server
api.add_resource(LyricsAPI._Create, '/create/', '/create/<lyric>')
api.add_resource(LyricsAPI._Read, "", '/')
api.add_resource(LyricsAPI._ReadID, '/<int:id>', '/<int:id>/')
api.add_resource(LyricsAPI._ReadRandom, '/random', '/random/')
api.add_resource(LyricsAPI._ReadCount, '/count', '/count/')
api.add_resource(LyricsAPI._UpdateLove, '/love/<int:id>', '/love/<int:id>/')
api.add_resource(LyricsAPI._UpdateDislike, '/dislike/<int:id>', '/dislike/<int:id>/')

if __name__ == "__main__":
    # server = "http://127.0.0.1:5000" # run local
    server = 'https://flask.opencodingsociety.com' # run from web
    url = server + "/api/lyrics"
    responses = [] # responses list

    # get count of lyrics on server
    count_response = requests.get(url+"/count")
    count_json = count_response.json()
    count = count_json['count']

    # update loves/dislikes test sequence
    num = str(random.randint(0, count-1)) # test a random record
    responses.append(
        requests.get(url+"/"+num) # read lyric by id
    )
    responses.append(
        requests.put(url+"/love/"+num) # add to love count
    )
    responses.append(
        requests.put(url+"/dislike/"+num) # add to dislike count
    )

    # obtain a random lyric
    responses.append(
        requests.get(url+"/random") # read a random lyric
    )

    # cycle through responses
    for response in responses:
        print(response)
        try:
            print(response.json())
        except:
            print("unknown error")