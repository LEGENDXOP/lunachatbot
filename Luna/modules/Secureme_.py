from Luna import tbot
from Luna.events import register
import secureme
@register(pattern="^/encrypt (.*)")
async def hmm(event):
    cmd = event.pattern_match.group(1)
    Text = cmd
    k = secureme.encrypt(Text)
    await event.reply(k)

@register(pattern="^/decrypt (.*)")
async def hmm(event):
    ok = event.pattern_match.group(1)
    Text = ok
    k = secureme.decrypt(Text)
    await event.reply(k)
