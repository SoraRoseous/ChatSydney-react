import asyncio
import json

import websockets
from EdgeGPT import Chatbot
from aiohttp import web


async def handle_client(websocket):
    try:
        async for message in websocket:
            request = json.loads(message)
            user_message = request['message']
            context = request['context']
            async for response in process_message(user_message, context):
                await websocket.send(json.dumps(response))
    except websockets.ConnectionClosedError:
        pass


async def process_message(user_message, context):
    chatbot = None
    try:
        chatbot = await Chatbot.create(cookie_path="cookies.json")
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
    return web.FileResponse('.' + file_path)


async def main():
    app = web.Application()
    app.router.add_get('/{tail:.*}', http_handler)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, 'localhost', 65432)
    await site.start()
    print("Go to http://localhost:65432 to start chatting!")

    start_server = websockets.serve(handle_client, 'localhost', 54321)
    await start_server


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(main())
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        loop.close()
