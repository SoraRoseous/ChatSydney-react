import asyncio
import json
import os

from slack_sdk.web.async_client import AsyncWebClient

if os.path.exists("claude.json"):
    with open("claude.json") as f:
        try:
            claude_config = json.load(f)
        except json.JSONDecodeError:
            claude_config = {}
else:
    claude_config = {}


class Chatbot:
    def __init__(
            self,
            slack_user_token=claude_config.get("slackUserToken"),
            slack_channel_id=claude_config.get("slackChannelId"),
            claude_member_id=claude_config.get("claudeMemberId"),
            proxy=None,
    ):
        self.client = AsyncWebClient(token=slack_user_token, proxy=proxy)
        self.slack_channel_id = slack_channel_id
        self.claude_member_id = claude_member_id

    async def ask_stream(self, message):
        if len(message) < 3000:  # Slack truncates message at ~3000 characters
            response = await self.client.chat_postMessage(channel=self.slack_channel_id, text=message)
            thread_ts = response["ts"]
        else:
            response = await self.client.chat_postMessage(channel=self.slack_channel_id, text=message[:3000])
            thread_ts = response["ts"]
            await self.client.chat_postMessage(
                channel=self.slack_channel_id,
                text=message[3000:],
                thread_ts=thread_ts,
            )

        await self.client.chat_postMessage(
            channel=self.slack_channel_id,
            text=f'<@{self.claude_member_id}> [assistant](#message)',
            thread_ts=thread_ts,
        )

        while True:
            await asyncio.sleep(1)
            replies_response = await self.client.conversations_replies(channel=self.slack_channel_id, ts=thread_ts)
            all_replies = replies_response["messages"]
            for reply in all_replies:
                if reply["user"] == self.claude_member_id:
                    break
            else:
                continue

            if reply["text"].endswith("_Typing…_"):
                yield reply["text"][:-11]
            else:
                yield reply["text"]
                break
