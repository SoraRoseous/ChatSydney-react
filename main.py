import argparse
import asyncio
import json
import os
import traceback
import emoji
import claude
import time

from SydneyGPT.SydneyGPT import Chatbot
from BingImageCreator import ImageGenAsync
from aiohttp import web

public_dir = '/public'


async def sydney_process_message(user_message, context, _U, locale):
    chatbot = None
    # Set the maximum number of retries
    max_retries = 5
    for i in range(max_retries + 1):
        try:
            if _U:
                cookies = loaded_cookies + [{"name": "_U", "value": _U}]
            else:
                cookies = loaded_cookies
            #Used to save image links temporarily
            resp_txt = ""
            draw = False
            chatbot = await Chatbot.create(cookies=cookies, proxy=args.proxy)
            async for _, response in chatbot.ask_stream(prompt=user_message, conversation_style="creative", raw=True,
                                                        webpage_context=context, search_result=True, locale=locale):
                #Support for generating images
                if (
                    (response.get("type") == 1)
                    and ("messages" in response["arguments"][0])
                    and (
                        response["arguments"][0]["messages"][0].get(
                            "messageType",
                        )
                        == "GenerateContentQuery"
                    )
                ):
                    async with ImageGenAsync(all_cookies=cookies) as image_generator:
                        images = await image_generator.get_images(
                            response["arguments"][0]["messages"][0]["text"],
                        )
                    for i, image in enumerate(images):
                        resp_txt = f"{resp_txt}\n![image{i}]({image})"
                    draw = True

                elif response.get("type") == 2 and draw:
                    # add pictures to previous messages
                    response["item"]["messages"][1]["adaptiveCards"][0]["body"][0]["text"] += resp_txt

                yield response
            break
        except TimeoutError:
            if i < max_retries:
                print("Retrying...", i + 1, "attempts.")
                # wait two second
                time.sleep(2) 
            else:
                print("Failed after", max_retries, "attempts.")
                print({"type": "error", "error": traceback.format_exc()})
                yield {"type": "error", "error": traceback.format_exc()}
        except Exception as e:
            if str(e) == "Bad images":
                print("Bad images")
            yield {"type": "error", "error": traceback.format_exc()}
            break
        finally:
            if chatbot:
                await chatbot.close()


async def claude_process_message(context):
    try:
        async for reply in claude_chatbot.ask_stream(context):
            yield {"type": "reply", "text": emoji.emojize(reply, language='alias').strip()}
        yield {"type": "finished"}
    except:
        yield {"type": "error", "error": traceback.format_exc()}


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

    async def monitor():
        while True:
            if ws.closed:
                task.cancel()
                break
            await asyncio.sleep(0.1)

    async def main_process():
        async for msg in ws:
            if msg.type == web.WSMsgType.TEXT:
                request = json.loads(msg.data)
                user_message = request['message']
                context = request['context']
                locale = request['locale']
                _U = request.get('_U')
                bot_type = request.get("botType", "Sydney")
                if bot_type == "Sydney":
                    async for response in sydney_process_message(user_message, context, _U, locale=locale):
                        await ws.send_json(response)
                elif bot_type == "Claude":
                    async for response in claude_process_message(context):
                        await ws.send_json(response)
                else:
                    print(f"Unknown bot type: {bot_type}")

    task = asyncio.ensure_future(main_process())
    monitor_task = asyncio.ensure_future(monitor())
    done, pending = await asyncio.wait([task, monitor_task], return_when=asyncio.FIRST_COMPLETED)

    for task in pending:
        task.cancel()

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
    parser.add_argument("--proxy", "-p", help='proxy address like "http://localhost:7890"', default="http://localhost:7890")
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

    claude_chatbot = claude.Chatbot(proxy=args.proxy)

    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(main(host, port))
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        loop.close()
