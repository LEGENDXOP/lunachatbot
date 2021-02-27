from Luna import SUDO_USERS, OWNER_ID, tbot, DEV_USERS
from Luna.events import register
from telethon.tl.types import ChatBannedRights
from telethon import events
from telethon.tl.functions.channels import EditBannedRequest

@register(pattern="^/alive")
async def alive(event):
    if event.sender_id == OWNER_ID:
        await event.reply("I'm Alive Master")
    elif event.sender_id in DEV_USERS:
        await event.reply("I'm Alive Co-Master")
    elif event.sender_id in SUDO_USERS:
        await event.reply("I'm Alive Pro!")
    elif event.sender_id not in SUDO_USERS:
        await event.reply("★彡[Anie]彡★")

@register(pattern="^/die")
async def alive(event):
    if event.sender_id == OWNER_ID:
        await event.reply("Ok Master 🤐")
    elif event.sender_id in DEV_USERS:
        await event.reply("Hmm")
    elif event.sender_id in SUDO_USERS:
        await event.reply("Jnl")
    elif event.sender_id not in SUDO_USERS:
        await event.reply("Soon..")
