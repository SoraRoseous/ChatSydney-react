# ChatSydney

## Installation

First, you need to have Python 3.11 or higher installed. Then, you can install the required dependencies using pip:

```bash
pip install -r requirements.txt --upgrade
```

## Usage

You can run this project using the Python command line:

```bash
python main.py
```

Then, you can open `http://localhost:65432` in your browser to start chatting.

## Command Line Arguments

- `--host` or `-H`: The hostname and port for the server, default is `localhost:65432`.
- `--proxy` or `-p`: Proxy address, like `http://localhost:7890`, default is empty.

## WebSocket API

The WebSocket API accepts a JSON object containing the following fields:

- `message`: The user's message.
- `context`: The context of the conversation, can be any string.

The WebSocket API returns a JSON object containing the following fields:

- `type`: The type of the message, can be the type from Bing response or `error`.
- `message`: The response from EdgeGPT.
- `error`: If an error occurs, this field will contain the error message.
