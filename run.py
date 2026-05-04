from psycogreen.gevent import patch_psycopg
patch_psycopg()

from project import create_app, socketio

app = create_app()

if __name__ == "__main__":
    socketio.run(app)