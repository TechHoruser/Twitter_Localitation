# Interesting Tools
# https://api.twitter.com/oauth/request_token

import twitter
import json
import requests
import urlparse
import datetime
import oauth2
import re
import sys
import httplib, urllib

from datetime import timedelta
from flask import Flask, request, render_template, redirect
from flask.ext.googlemaps import GoogleMaps
from flask.ext.googlemaps import Map

CONSUMER_KEY='OLDLHqzjpVgOndpKVOlv2Wt23'
CONSUMER_SECRET='y5q0NHmRRiTZZrcWcTnCgIiXBsU29FGUC2cqtcYGca9eADFZrk'
OAUTH_TOKEN = ""
OAUTH_TOKEN_SECRET = ""

consumer = ""
request_token = ""

usuarios = set()

def cargarFichero():
    global usuarios

    f=file("nombres_usuarios", "r")
    lines=f.read().split()
    f.close()
    for line in lines:
        usuarios.add(line)

def guardarFichero():
    f=file("nombres_usuarios","w");
    for u in usuarios:
        f.write(u+"\n")
    f.close()

def streamFun():
    # ThingSpeak
    params = urllib.urlencode({'field1': len(usuarios), 'key':'L9TUFV056YFBZKV5'})
    headers = {"Content-type": "application/x-www-form-urlencoded","Accept": "text/plain"}
    conn = httplib.HTTPConnection("api.thingspeak.com:80")
    conn.request("POST", "/update", params, headers)
    response = conn.getresponse()
    print "Thingspeak - ", response.status, response.reason

    data = response.read()
    conn.close()

def oauth_login():
    global access_token
    global api

    auth = twitter.oauth.OAuth(OAUTH_TOKEN, OAUTH_TOKEN_SECRET, CONSUMER_KEY, CONSUMER_SECRET)
    #twitter_api = twitter.Twitter(auth=access_token) tenias esto puesto pero da error
    twitter_api = twitter.Twitter(auth=auth)
    return twitter_api

def friendlist(tw,tweetsamount):
    user = tw.account.verify_credentials()

    query = tw.friends.ids(screen_name = user['screen_name'])
    twetts = []

    if tweetsamount > 100:
        tweetsamount = 100

    for e in query['ids']:
        twetts.append(tw.statuses.user_timeline(user_id = e, count = tweetsamount))

    
    return geo(twetts)

def geo(lista):
    listado=[]
    
    for resultado2 in lista:
        for resultado in resultado2:
            # only process a result if it has a geolocation
            if resultado["place"]:
                #(resultado["place"]["bounding_box"]["coordinates"][0])
                momento = datetime.datetime.strptime(resultado["created_at"], '%a %b %d %H:%M:%S +0000 %Y') + timedelta(hours=1)
                latitud = 0
                longitud = 0
                for e in resultado["place"]["bounding_box"]["coordinates"][0]:
                    latitud += e[0]
                    longitud += e[1]
                latitud = latitud/len(resultado["place"]["bounding_box"]["coordinates"][0])
                longitud = longitud/len(resultado["place"]["bounding_box"]["coordinates"][0])
                
                momento = momento + datetime.timedelta(hours=1)
                listado.append({"id":resultado["id"], "lugar" : resultado["place"]["full_name"], "momento" : momento, "latitud" : latitud, "longitud" : longitud, "usuario":resultado["user"]})
                break
            
    return listado


def login1():
    global consumer
    global request_token
    
    request_token_url='https://api.twitter.com/oauth/request_token'
    authorize_url='https://api.twitter.com/oauth/authorize'

    consumer=oauth2.Consumer(CONSUMER_KEY,CONSUMER_SECRET)
    client=oauth2.Client(consumer)
    resp, content = client.request(request_token_url, "GET")

    if resp['status'] != '200':
        raise Exception("Invalid response %s." % resp['status'])

    request_token = dict(urlparse.parse_qsl(content))
    url = "%s?oauth_token=%s" % (authorize_url, request_token['oauth_token'])

    return render_template('twitter.html', url=url)


def login2(pin,tweetsamount):
    global consumer
    global request_token
    global OAUTH_TOKEN
    global OAUTH_TOKEN_SECRET
    global access_token

    access_token_url='https://api.twitter.com/oauth/access_token'

    token = oauth2.Token(request_token['oauth_token'],request_token['oauth_token_secret'])
     
    token.set_verifier(pin)
    client = oauth2.Client(consumer, token)

    resp, content = client.request(access_token_url, "POST")
    access_token = dict(urlparse.parse_qsl(content))

    OAUTH_TOKEN = access_token["oauth_token"]
    OAUTH_TOKEN_SECRET = access_token["oauth_token_secret"]

    return friends(tweetsamount)


def friends(tweetsamount):
    global usuarios

    listado = friendlist(oauth_login(),tweetsamount)
    l={}

    for e in listado:
        usuarios.add(e['usuario']['screen_name'])
        l.update({e['usuario']['profile_image_url']:[(e['longitud'],e['latitud'])]})

    mapa = Map(
        identifier="view-side",
        lat=40.3450396,
        lng=-3.6517684,
        zoom=6,
        markers=l,
        style="height:600px;width:800px;margin:0;"
    )

    guardarFichero()
    # Actualizamos valores de ThingSpeak
    streamFun()

    return render_template('mapa.html', mapa=mapa, tag="AMIGOS", listado=listado)

cargarFichero()

app = Flask(__name__)
GoogleMaps(app)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/twitter/')
def twitter_function():
    return login1()

@app.route('/twitter/pin/', methods=['POST'])
def twitterpin():
    return login2(request.form['pin'],request.form['tweetsamount'])

@app.route('/twitter/ruta/', methods=['POST'])
def twitteruta():
    option = request.form['marca']
    expresion = re.compile('Longitud: (.*)? Latitud: (.*)?')
    g = expresion.findall(option)
    uri = "https://www.google.es/maps/dir//"+g[0][0]+","+g[0][1]
    return redirect(uri)

if __name__ == "__main__":
    if len(sys.argv) == 1:
        app.run(debug=True, host="localhost")
    else:
        app.run(debug=True, host=sys.argv[1])
