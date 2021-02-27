
from Luna.events import register
from Luna import CMD_HELP
from Luna import tbot as borg
from Luna import tbot
from Luna import OWNER_ID, SUDO_USERS
from Luna import TEMP_DOWNLOAD_DIRECTORY
import os
from shutil import rmtree
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
import pytz 
import asyncio
import requests
from PIL import Image, ImageDraw, ImageFont
from telegraph import upload_file
import time
import html
from telethon.tl.functions.photos import GetUserPhotosRequest
from telethon.tl.functions.users import GetFullUserRequest
from telethon.tl.types import MessageEntityMentionName
from telethon.utils import get_input_location
sedpath = "./lunabot/"
if not os.path.isdir(sedpath):
    os.makedirs(sedpath)
from Luna.defs import convert_to_image, crop_vid, runcmd, tgs_to_gif
OP = "58199388-5499-4c98-b052-c679b16310f9"
@register(pattern="^/nfsw")
async def hmm(event):
    if event.fwd_from:
        return
    life = OP
    if not event.reply_to_msg_id:
        await event.reply("Reply to any Image.")
        return
    headers = {"api-key": life}
    hmm = await event.reply("Detecting..")
    await event.get_reply_message()
    img = await convert_to_image(event, borg)
    img_file = {
        "image": open(img, "rb"),
    }
    url = "https://api.deepai.org/api/nsfw-detector"
    r = requests.post(url=url, files=img_file, headers=headers).json()
    sedcopy = r["output"]
    hmmyes = sedcopy["detections"]
    game = sedcopy["nsfw_score"]
    await hmm.delete()
    final = f"**IMG RESULT** \n**Detections :** `{hmmyes}` \n**NSFW SCORE :** `{game}`"
    await borg.send_message(event.chat_id, final)
    await hmm.delete()
    if os.path.exists(img):
        os.remove(img)