import argparse
import asyncio
import json

from aiohttp import web

from EdgeGPT import Chatbot


async def process_message(user_message, context):
    chatbot = None
    try:
        chatbot = await Chatbot.create(cookie_path="cookies.json", proxy=args.proxy)
        async for _, response in chatbot.ask_stream(prompt=user_message, conversation_style="creative", raw=True,
                                                    webpage_context=context, search_result=True):
            yield response
    except Exception as e:
        yield {"type": "error", "error": str(e)}
    finally:
        if chatbot:
            await chatbot.close()


async def http_handler(request):
    file_path = request.path
    if file_path == "/":
        file_path = "/index.html"
    response = web.FileResponse('.' + file_path)
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
            async for response in process_message(user_message, context):
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
    parser.add_argument("--proxy", "-p", help='proxy address like "http://localhost:7890"', default="")
    args = parser.parse_args()

    host, port = args.host.split(":")
    port = int(port)

    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(main(host, port))
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        loop.close()
