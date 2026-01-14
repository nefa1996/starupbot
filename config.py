import os

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))
TON_WALLET = os.getenv("TON_WALLET")
MIN_REWARD = float(os.getenv("MIN_REWARD", 1.0))
LOG_CHANNELS = os.getenv("LOG_CHANNELS", "").split(",")