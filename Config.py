import os
ENV = bool(os.environ.get("ENV", False))
if ENV:
    import os
    class Config(object):
        bot_id = os.environ.get("BOT_ID", None)
        bot_token = os.environ.get("TOKEN", None)
        owner_id = os.environ.get("OWNER_ID", None)
else:
    class Config(object):
        owner_id = None
        bot_token = None
        bot_id = None
