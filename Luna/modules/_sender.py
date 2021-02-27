from Luna import tbot, OWNER_ID
from Luna.events import register
import os
import asyncio
import os
import time
from datetime import datetime
from Luna import TEMP_DOWNLOAD_DIRECTORY as path
from Luna import TEMP_DOWNLOAD_DIRECTORY
from datetime import datetime
from Luna.defs import progress

client = tbot
@register(pattern=r"^/send ?(.*)")
async def Prof(event):
    if event.sender_id == OWNER_ID:
        pass
    else:
        return
    message_id = event.message.id
    input_str = event.pattern_match.group(1)
    the_plugin_file = "./julia/modules/{}.py".format(input_str)
    if os.path.exists(the_plugin_file):
     message_id = event.message.id
     await event.client.send_file(
             event.chat_id,
             the_plugin_file,
             force_document=True,
             allow_cache=False,
             reply_to=message_id,
         )
    else:
        await event.reply("Are You On Weed?,No Such File Exist!")

thumb_image_path = TEMP_DOWNLOAD_DIRECTORY + "thumb_image.jpg"
client = tbot
@register(pattern="^/ren ?(.*)")
async def _(event):
    if event.fwd_from:
        return
    thumb = None
    if os.path.exists(thumb_image_path):
        thumb = thumb_image_path
    dcevent = await event.reply(
        "Rename & Upload in process 🙄🙇‍♂️🙇‍♂️🙇‍♀️ It might take some time if file size is big",
    )
    input_str = event.pattern_match.group(1)
    if not os.path.isdir(TEMP_DOWNLOAD_DIRECTORY):
        os.makedirs(TEMP_DOWNLOAD_DIRECTORY)
    if event.reply_to_msg_id:
        start = datetime.now()
        file_name = input_str
        reply_message = await event.get_reply_message()
        c_time = time.time()
        to_download_directory = TEMP_DOWNLOAD_DIRECTORY
        downloaded_file_name = os.path.join(to_download_directory, file_name)
        downloaded_file_name = await event.client.download_media(
            reply_message,
            downloaded_file_name,
            progress_callback=lambda d, t: asyncio.get_event_loop().create_task(
                progress(d, t, dcevent, c_time, "trying to download", file_name)
            ),
        )
        end = datetime.now()
        ms_one = (end - start).seconds
        try:
            thumb = await reply_message.download_media(thumb=-1)
        except Exception:
            thumb = thumb
        if os.path.exists(downloaded_file_name):
            c_time = time.time()
            hmm = await event.client.send_file(
                event.chat_id,
                downloaded_file_name,
                force_document=False,
                supports_streaming=True,
                allow_cache=False,
                reply_to=event.message.id,
                thumb=thumb,
                progress_callback=lambda d, t: asyncio.get_event_loop().create_task(
                    progress(
                        d, t, event, c_time, "trying to upload", downloaded_file_name
                    )
                ),
            )
            end_two = datetime.now()
            os.remove(downloaded_file_name)
            ms_two = (end_two - end).seconds
            await dcevent.edit(
                f"Downloaded file in {ms_one} seconds.\nUploaded in {ms_two} seconds."
            )
            await asyncio.sleep(2)
        else:
            await dcevent.edit("File Not Found {}".format(input_str))
    else:
        await dcevent.reply(".rename file.name as reply to a Telegram media/file")

import asyncio
import os
import time
from datetime import datetime
from io import BytesIO
from pathlib import Path
from Luna import tbot as borg
from telethon import functions, types
from telethon.errors import PhotoInvalidDimensionsError
from telethon.errors.rpcerrorlist import YouBlockedUserError
from telethon.tl.functions.messages import SendMediaRequest
@register(pattern="^/dox ?(.*)")
async def get(event):
    name = event.text[5:]
    if name is None:
        await event.reply("reply to text message as `.ttf <file name>`")
        return
    m = await event.get_reply_message()
    if m.text:
        with open(name, "w") as f:
            f.write(m.message)
        await event.delete()
        await event.client.send_file(event.chat_id, name, force_document=True)
        os.remove(name)
    else:
        await event.reply("reply to text message as `.ttf <file name>`")

from Luna.events import load_module
import asyncio
import os
from datetime import datetime
from pathlib import Path

@register(pattern="^/install")
async def install(event):
    if event.fwd_from:
        return
    if event.reply_to_msg_id:
        try:
            downloaded_file_name = (
                await event.client.download_media(  # pylint:disable=E0602
                    await event.get_reply_message(),
                    "Luna/modules/",  # pylint:disable=E0602
                )
            )
            if "(" not in downloaded_file_name:
                path1 = Path(downloaded_file_name)
                shortname = path1.stem
                load_module(shortname.replace(".py", ""))
                await event.reply("Installed.... Ab Full Masti💥\n `{}`".format(
                        os.path.basename(downloaded_file_name)
                    ),
                )
            else:
                os.remove(downloaded_file_name)
                await event.reply("**Error!**\nCannot Install!\n Or Pre Installed Meybe..",
                )
        except Exception as e:  # pylint:disable=C0103,W0703
            await event.reply(str(e))
            os.remove(downloaded_file_name)
    await asyncio.sleep(3)
    await event.delete()
