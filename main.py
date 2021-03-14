import os
import re
from json import loads as json_loads

import requests
from pyrogram import Client, filters
from pyrogram.types import Message, InputMediaPhoto

if not os.getenv('DOCKER'):
    from dotenv import load_dotenv

    load_dotenv()

app = Client(':memory:', os.getenv('API_ID'), os.getenv('API_HASH'), bot_token=os.getenv('BOT_TOKEN'))
PIXIV_LINK_PATTERN = re.compile(r'(https?://)(www\.)?pixiv\.net(/en)?/artworks/(\d+)', re.I)


@app.on_message(filters.command('start'))
def on_cmd_start(_: Client, message: Message):
    message.reply_text("Hi! Send me `/pixiv <link>` and I'll send you pics.", parse_mode='Markdown')


@app.on_message(filters.command('pixiv') & filters.regex(PIXIV_LINK_PATTERN))
def on_cmd_pixiv(_: Client, message: Message):
    artwork_id = PIXIV_LINK_PATTERN.search(message.text).groups()[-1]
    response = requests.get(f'https://www.pixiv.net/en/artworks/{artwork_id}')
    if response.status_code != 200:
        message.reply_text("Got non 200 status code.")
        return
    data = json_loads(
        re.search(r"""<meta name="preload-data" id="meta-preload-data" content='(.+)'>""", response.text, re.I).group(1)
    )
    filenames = []
    for page in range(data['illust'][str(artwork_id)]['pageCount']):
        source = 'original'
        file_url = data['illust'][str(artwork_id)]['urls'][source].replace('_p0', f'_p{page}')
        response_headers = requests.head(file_url, headers={'Referer': 'https://www.pixiv.net/'})
        if response_headers.status_code != 200:
            continue
        if 'Content-Length' in response_headers.headers:
            if int(response_headers.headers['Content-Length']) >= 1000000:
                source = 'regular'
                file_url = data['illust'][str(artwork_id)]['urls'][source].replace('_p0', f'_p{page}')
                response_headers = requests.head(file_url, headers={'Referer': 'https://www.pixiv.net/'})
                if response_headers.status_code != 200:
                    continue
                if int(response_headers.headers['Content-Length']) >= 1000000:
                    source = 'small'
                    file_url = data['illust'][str(artwork_id)]['urls'][source].replace('_p0', f'_p{page}')
                    response_headers = requests.head(file_url, headers={'Referer': 'https://www.pixiv.net/'})
                    if response_headers.status_code != 200:
                        continue
                    if int(response_headers.headers['Content-Length']) >= 1000000:
                        continue
        response = requests.get(file_url, headers={'Referer': 'https://www.pixiv.net/'})
        filename = file_url.split('/')[-1]
        try:
            with open(filename, 'wb') as fp:
                fp.write(response.content)
                fp.close()
            if os.path.getsize(filename) <= 10000000:
                filenames.append(filename)
        except:
            message.reply_text("Couldn't save file.")
    sent_messages = message.reply_media_group(
        [InputMediaPhoto(filenames[0],
                         '<a href="{}">{}</a>'.format(
                             f'https://www.pixiv.net/en/artworks/{artwork_id}',
                             data['illust'][str(artwork_id)]['title']
                         )
                         )] +
        [InputMediaPhoto(filename) for filename in filenames[1:10]],
        False
    )
    for i in range(10, len(filenames), 10):
        sent_messages[0].reply_media_group([InputMediaPhoto(filename) for filename in filenames[i:i + 10]], True)
    try:
        message.delete()
    except:
        pass
    for filename in filenames:
        try:
            os.remove(filename)
        except:
            continue


if __name__ == '__main__':
    app.run()
