import os, socket, sys
os.environ.update(TERMINAL_SIN_MOTOR='1', TERMINAL_SIN_ENV='1', TERMINAL_MODO='real')
os.environ['TERMINAL_DATA_DIR']=sys.argv[1]
sys.path.insert(0,r'C:\Users\MIKE\Desktop\Repos\actinver-terminal')
original=socket.socket.connect
def local(self,address):
    if isinstance(address,tuple) and address[0] not in ('127.0.0.1','::1','localhost'):
        raise OSError('Prueba offline: conexión externa bloqueada')
    return original(self,address)
socket.socket.connect=local
import uvicorn
from pathlib import Path
Path(sys.argv[1]+'/pid.txt').write_text(str(os.getpid()))
uvicorn.run('terminal.app:app',host='127.0.0.1',port=8796,log_level='critical',access_log=False)
