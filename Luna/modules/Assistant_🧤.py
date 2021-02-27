from Luna import CMD_HELP
from Luna import tbot
import os
import subprocess

import requests
from gtts import gTTS
from gtts import gTTSError
from requests import get
from telethon import *
from telethon.tl import functions
from telethon.tl import types
from telethon.tl.types import *

from Luna import *

from Luna.events import register




@register(pattern=r"^/luna(?: |$)([\s\S]*)")
async def _(event):
    if event.fwd_from:
        return
    if not event.reply_to_msg_id:
        i = event.pattern_match.group(1)
        appid = WOLFRAM_ID
        server = f"https://api.wolframalpha.com/v1/spoken?appid={appid}&i={i}"
        res = get(server)
        if res == "Wolfram Alpha did not understand your input":
           await event.reply("Sorry I can't understand")
           return   
        await event.reply(f"**{i}**\n\n" + res.text, parse_mode="markdown")

    if event.reply_to_msg_id:
        previous_message = await event.get_reply_message()
        required_file_name = await tbot.download_media(
            previous_message, TEMP_DOWNLOAD_DIRECTORY)
        if IBM_WATSON_CRED_URL is None or IBM_WATSON_CRED_PASSWORD is None:
            await event.reply(
                "You need to set the required ENV variables for this module. \nModule stopping"
            )
        else:
            headers = {
                "Content-Type": previous_message.media.document.mime_type,
            }
            data = open(required_file_name, "rb").read()
            response = requests.post(
                IBM_WATSON_CRED_URL + "/v1/recognize",
                headers=headers,
                data=data,
                auth=("apikey", IBM_WATSON_CRED_PASSWORD),
            )
            r = response.json()
            if "results" in r:
                # process the json to appropriate string format
                results = r["results"]
                transcript_response = ""
                transcript_confidence = ""
                for alternative in results:
                    alternatives = alternative["alternatives"][0]
                    transcript_response += " " + str(
                        alternatives["transcript"])
                if transcript_response != "":
                    string_to_show = "{}".format(transcript_response)
                    appid = WOLFRAM_ID
                    server = f"https://api.wolframalpha.com/v1/spoken?appid={appid}&i={string_to_show}"
                    res = get(server)
                    answer = res.text
                    try:
                        tts = gTTS(answer, tld="com", lang="en")
                        tts.save("results.mp3")
                    except AssertionError:
                        return
                    except ValueError:
                        return
                    except RuntimeError:
                        return
                    except gTTSError:
                        return
                    with open("results.mp3", "r"):
                        await tbot.send_file(
                            event.chat_id,
                            "results.mp3",
                            voice_note=True,
                            reply_to=event.id,
                        )
                    os.remove("results.mp3")
                    os.remove(required_file_name)
                elif transcript_response == "Wolfram Alpha did not understand your input":
                    try:
                        answer = "Sorry I can't understand"
                        tts = gTTS(answer, tld="com", lang="en")
                        tts.save("results.mp3")
                    except AssertionError:
                        return
                    except ValueError:
                        return
                    except RuntimeError:
                        return
                    except gTTSError:
                        return
                    with open("results.mp3", "r"):
                        await tbot.send_file(
                            event.chat_id,
                            "results.mp3",
                            voice_note=True,
                            reply_to=event.id,
                        )
                    os.remove("results.mp3")
                    os.remove(required_file_name)
            else:
                await event.reply("API Failure !")
                os.remove(required_file_name)


