import sys
import websocket
import tornado.escape


if __name__ == "__main__":
    try:
        m = sys.argv[1]
    except IndexError:
        print('Pass "list" or "message" as an argument')
        sys.exit()

    if m == 'list':
        message = {'type': 'get_user_list'}
    elif m == 'message':
        message = {'type': 'message', 'message': 'Hello', 'to': 1}
    else:
        message = {}

    ws = websocket.create_connection("ws://127.0.0.1:8888/chatsocket")
    ws.send(
        tornado.escape.json_encode(message)
    )
    result = ws.recv()
    print(tornado.escape.json_decode(result))
    result = ws.recv()
    print(tornado.escape.json_decode(result))
    # ws.close()
