import websocket
import tornado.escape


if __name__ == "__main__":
    ws = websocket.create_connection("ws://127.0.0.1:8888/chatsocket")
    ws.send(
        tornado.escape.json_encode({'type': 'get_user_list'})
    )
    result = ws.recv()
    print(tornado.escape.json_decode(result))
    ws.close()
