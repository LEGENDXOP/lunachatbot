import requests
from Luna import tbot
from Luna.events import register
url = "https://iamai.p.rapidapi.com/ask"

@register(pattern="^/test (.*)")
async def hmm(event):
  test = event.pattern_match.group(1)
  r = ('\n    \"consent\": true,\n    \"ip\": \"::1\",\n    \"question\": \"{}\"\n').format(test)
  k = f"({r})"
  new_string = k.replace("(", "{")
  lol = new_string.replace(")","}")
  payload = lol
  headers = {
      'content-type': "application/json",
      'x-forwarded-for': "<user's ip>",
      'x-rapidapi-key': "fef481fee3mshf99983bfc650decp104100jsnbad6ddb2c846",
      'x-rapidapi-host': "iamai.p.rapidapi.com"
      }

  response = requests.request("POST", url, data=payload, headers=headers)
  lodu = response.json()
  result = (lodu['message']['text'])
  await event.reply(result)

import requests
from telethon import events
from Luna import tbot

@tbot.on(events.NewMessage(pattern=None))
async def check_message(event):
    if event.is_group:
        pass
    else:
        return
    message = str(event.text)
    reply_msg = await event.get_reply_message()
    if message.lower() == "Luna":
        return True
    if reply_msg:
        if reply_msg.sender_id == BOT_ID:
            return True
    else:
        return False


@tbot.on(events.NewMessage(pattern=None))
async def _(event):
    if event.is_group:
        pass
    else:
        return

    msg = str(event.text)
    if not is_chat:
        return
    if msg:
        test = msg
        r = ('\n    \"consent\": true,\n    \"ip\": \"::1\",\n    \"question\": \"{}\"\n').format(test)
        k = f"({r})"
        new_string = k.replace("(", "{")
        lol = new_string.replace(")","}")
        payload = lol
        headers = {
      'content-type': "application/json",
      'x-forwarded-for': "<user's ip>",
      'x-rapidapi-key': "fef481fee3mshf99983bfc650decp104100jsnbad6ddb2c846",
      'x-rapidapi-host': "iamai.p.rapidapi.com"
      }

        response = requests.request("POST", url, data=payload, headers=headers)
        lodu = response.json()
        result = (lodu['message']['text'])
        await event.reply(result)
