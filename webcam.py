#from bottle import Bottle
import bottle
from bottle import response
import os
from PIL import Image
import requests, wsgiserver


host_addr = '0.0.0.0'
host_port = 8888
root = '/webcam'

#cam_addr = '192.168.1.108'
#cam_usr = 'admin'
#cam_pass = 'admin'
cam_addr = os.environ['CAM_ADDR']
cam_usr = os.environ['CAM_USR']
cam_pass = os.environ['CAM_PASSWD']
cam_url = 'http://' + cam_addr
cam_name = "/cgi-bin/magicBox.cgi?action=getMachineName"
cam_image = "/cgi-bin/snapshot.cgi"

app = bottle.app()
#app = Bottle()


# the decorator
def enable_cors(fn):
    def _enable_cors(*args, **kwargs):
        # set CORS headers
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Origin, Accept, Content-Type, X-Requested-With, X-CSRF-Token'

        if bottle.request.method != 'OPTIONS':
            # actual request; reply with the actual response
            return fn(*args, **kwargs)

    return _enable_cors


@app.route(root + '/test', method=['GET'])
def test():

    return {'status': 'success', 'message': 'Hello,world!', 'data': None}


@app.route(root + '/image', method=['GET'])
@enable_cors
def get_webcam_image():
    try:
        auth = requests.auth.HTTPBasicAuth(cam_usr,cam_pass)
        rep = requests.get(cam_url + cam_image, auth = auth)
        rep.raise_for_status()
    except requests.HTTPError:
        auth = requests.auth.HTTPDigestAuth(cam_usr,cam_pass)
        rep = requests.get(cam_url + cam_image, auth = auth)

    return rep


@app.route(root + '/name', method=['GET'])
def get_webcam_name():
    try:
        auth = requests.auth.HTTPBasicAuth(cam_usr,cam_pass)
        rep = requests.get(cam_url + cam_name, auth = auth)
        rep.raise_for_status()
    except requests.HTTPError:
        auth = requests.auth.HTTPDigestAuth(cam_usr,cam_pass)
        rep = requests.get(cam_url + cam_name, auth = auth)

    return rep


def main():
    server = wsgiserver.WSGIServer(app, host=host_addr, port=int(host_port))
    server.start()

if __name__ == '__main__':
    main()
