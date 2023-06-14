import argparse
import asyncio
import json
import os
import traceback
import urllib.request

from EdgeGPT import Chatbot
from aiohttp import web

public_dir = '/public'


async def process_message(user_message, context, _U, locale):
    chatbot = None
    try:
        if _U:
            cookies = loaded_cookies + [{"name": "_U", "value": _U}]
        else:
            cookies = loaded_cookies
        chatbot = await Chatbot.create(cookies=cookies, proxy=args.proxy)
        async for _, response in chatbot.ask_stream(prompt=user_message, conversation_style="creative", raw=True,
                                                    webpage_context=context, search_result=True, locale=locale):
            yield response
    except:
        yield {"type": "error", "error": traceback.format_exc()}
    finally:
        if chatbot:
            await chatbot.close()


async def http_handler(request):
    file_path = request.path
    if file_path == "/":
        file_path = "/index.html"
    full_path = os.path.realpath('.' + public_dir + file_path)
    if not full_path.startswith(os.path.realpath('.' + public_dir)):
        raise web.HTTPForbidden()
    response = web.FileResponse(full_path)
    response.headers['Cache-Control'] = 'no-store'
    return response


async def websocket_handler(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)

    async for msg in ws:
        if msg.type == web.WSMsgType.TEXT:
            request = json.loads(msg.data)
            user_message = request['message']
            context = request['context']
            locale = request['locale']
            _U = request.get('_U')
            async for response in process_message(user_message, context, _U, locale=locale):
                await ws.send_json(response)

    return ws


async def main(host, port):
    app = web.Application()
    app.router.add_get('/ws/', websocket_handler)
    app.router.add_get('/{tail:.*}', http_handler)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()
    print(f"Go to http://{host}:{port} to start chatting!")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", "-H", help="host:port for the server", default="localhost:65432")
    parser.add_argument("--proxy", "-p", help='proxy address like "http://localhost:7890"',
                        default=urllib.request.getproxies().get('https'))
    args = parser.parse_args()
    print(f"Proxy used: {args.proxy}")

    host, port = args.host.split(":")
    port = int(port)

    if os.path.isfile("cookies.json"):
        with open("cookies.json", 'r') as f:
            loaded_cookies = json.load(f)
        print("Loaded cookies.json")
    else:
        loaded_cookies = []
        print("cookies.json not found")

    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(main(host, port))
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        loop.close()
