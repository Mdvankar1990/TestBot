import os

import requests

youtube_search_url = "https://www.googleapis.com/youtube/v3/search"
google_api_token = os.environ['GOOGLE_API_KEY']
base_yt_url = "https://www.youtube.com/xml/feeds/videos.xml?channel_id="
base_callback_url = os.environ['BASE_URL'] + "/feed/"
subscribe_url = "https://pubsubhubbub.appspot.com/subscribe"


# To subscribe to pubsubhubbub using channel id and feed id
def subscribe(channel_id: str):
    yt_url = base_yt_url + channel_id
    callback_url = base_callback_url + channel_id
    header = {
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36",
        "content-type": "application/x-www-form-urlencoded",
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
        "accept-encoding": "gzip, deflate, br",
        "accept-language": "en-GB,en-US;q=0.9,en;q=0.8",
        "sec-fetch-dest": "document"}
    body = {"hub.callback": callback_url,
            "hub.topic": yt_url,
            "hub.verify": "async",
            "hub.mode": "subscribe",
            "hub.verify_token": "",
            "hub.secret": "",
            "hub.lease_seconds": ""}
    response = requests.post(subscribe_url, headers=header, data=body)
    response.raise_for_status()
    return response.status_code


def youtube_search_by_channel(my_query: str):
    query = {"part": "snippet",
             "q": my_query,
             "type": "Channel",
             "key": google_api_token,
             "maxResults": 50}

    response = requests.get(url=youtube_search_url, params=query)
    try:
        response.raise_for_status()
    except:
        return "Error occured. Search again"
    items = response.json()['items']
    sel_channel_id = " "
    for item in items:
        if item['snippet']['title'] == my_query:
            sel_channel_id = item['snippet']['channelId']

    return sel_channel_id
