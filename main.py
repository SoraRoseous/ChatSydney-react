import argparse
import asyncio
import json
import os
import random
import traceback
import emoji
import httpx
import claude

from SydneyGPT.SydneyGPT import Chatbot
from aiohttp import web
from aiohttp.client_exceptions import ClientConnectorError

public_dir = '/public'

async def sydney_process_message(user_message, context, _U, locale, imgid):
    chatbot = None
    # Set the maximum number of retries
    max_retries = 5
    for i in range(max_retries + 1):
        try:
            if _U:
                cookies = list(filter(lambda d: d.get('name') != '_U', loaded_cookies)) + [{"name": "_U", "value": _U}]
            else:
                cookies = loaded_cookies
            chatbot = await Chatbot.create(cookies=cookies, proxy=args.proxy, imgid=imgid)
            async for _, response in chatbot.ask_stream(prompt=user_message, conversation_style="creative", raw=True,
                                                        webpage_context=context, search_result=True, locale=locale):
                yield response
            break
        except Exception as e:
            if (
                isinstance(e, TimeoutError)
                or isinstance(e, httpx.ConnectError)
                or isinstance(e, ClientConnectorError)
                or "Sorry, you need to login first to access this service." in str(e)
                or "ServiceClient failure for DeepLeo" in str(e)
            ) and i < max_retries:
                print("Retrying...", i + 1, "attempts.")
                # wait two second
                await asyncio.sleep(2)
            else:
                if i == max_retries:
                    print("Failed after", max_retries, "attempts.")
                traceback.print_exc()
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

# upload image
async def upload_image_handler(request):
    request_body = await request.json()
    if request_body['image']:
        upload_image = request_body['image']
        HEADERS_IMG = {
            "accept": "*/*",
            "accept-language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
            "sec-ch-ua": "\"Not.A/Brand\";v=\"8\", \"Chromium\";v=\"114\", \"Microsoft Edge\";v=\"114\"",
            "sec-ch-ua-arch": "\"x86\"",
            "sec-ch-ua-bitness": "\"64\"",
            "sec-ch-ua-full-version": "\"114.0.1823.67\"",
            "sec-ch-ua-full-version-list": "\"Not.A/Brand\";v=\"8.0.0.0\", \"Chromium\";v=\"114.0.5735.201\", \"Microsoft Edge\";v=\"114.0.1823.67\"",
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-model": "\"\"",
            "sec-ch-ua-platform": "\"Windows\"",
            "sec-ch-ua-platform-version": "\"14.0.0\"",
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "sec-ms-gec-version": "1-114.0.1823.67",
            "Referer": "https://www.bing.com/search?q=Bing+AI&showconv=1&FORM=hpcodx&wlsso=0",
            "Referrer-Policy": "origin-when-cross-origin"
        }
        files={
            'knowledgeRequest':(None, '{"imageInfo":{},"knowledgeRequest":{"invokedSkills":["ImageById"],"subscriptionId":"Bing.Chat.Multimodal","invokedSkillsRequestData":{"enableFaceBlur":true},"convoData":{"convoid":"","convotone":"Creative"}}}'),
            'imageBase64':(None, upload_image)
        }
        async with httpx.AsyncClient(
            proxies=args.proxy or None,
            timeout=30,
            headers={
                **HEADERS_IMG,
                "x-forwarded-for": f"13.{random.randint(104, 107)}.{random.randint(0, 255)}.{random.randint(0, 255)}",
            },
        ) as client:
            # Send POST request
            img_response = await client.post(
                url="https://www.bing.com/images/kblob",
                files=files
            )
        if img_response.status_code != 200:
            img_response.request.read()
            print(f"Status code: {img_response.status_code}")
            print(img_response.request.stream._stream.decode("utf-8"))
            raise Exception("Image upload failed")
        return web.json_response(img_response.text)
    else:
        raise Exception("No image.")

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
                if request.get('imgid'):
                    imgid = json.loads(request.get('imgid'))
                else:
                    imgid = None
                bot_type = request.get("botType", "Sydney")
                if bot_type == "Sydney":
                    async for response in sydney_process_message(user_message, context, _U, locale=locale, imgid=imgid):
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
    app.router.add_post('/upload_image/', upload_image_handler)
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
