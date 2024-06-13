from pyrogram import Client
from config import api_id, api_hash


# Create a Pyrogram client

app = Client('my_session', api_id=api_id, api_hash=api_hash)


app.run()
