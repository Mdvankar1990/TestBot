import json
import os
import requests
from bs4 import BeautifulSoup
from flask import Flask, request, Response
from flask_sqlalchemy import SQLAlchemy
from telebot import TeleBot
from pubsub import youtube_search_by_channel, subscribe

MINCREDIT = 20

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['DATABASE']
db = SQLAlchemy(app)
Token = os.environ["TELE_Token"]
bot = TeleBot(Token, parse_mode=None)
inp = bot.remove_webhook()
op = bot.set_webhook(url=os.environ['BASE_URL'])
youtube_video_base_url = "https://www.youtube.com/watch?v="
print(f"{inp}{op}")
###database tables and linkages
user_sub = db.Table("user_sub", db.Column('user_id', db.Integer, db.ForeignKey("user_table.user_id")),
                    db.Column('channel_id', db.Integer, db.ForeignKey("subscription_table.channel_id")))


class Users(db.Model):
    __tablename__ = "user_table"
    user_id = db.Column(db.Integer, primary_key=True)
    user_chat_id = db.Column(db.Integer, nullable=False, unique=True)
    user_name = db.Column(db.String(150), nullable=False)
    credit = db.Column(db.Integer, nullable=False)


class Subscription(db.Model):
    __tablename__ = "subscription_table"
    channel_id = db.Column(db.String(1000), primary_key=True)
    channel_name = db.Column(db.String(50), nullable=False)
    users = db.relationship("Users", secondary="user_sub", backref="subscriptions")


###message parsing and basic telegram functions
def tel_parse_message(message):
    # print("message-->", message)
    try:
        if "message" in message:
            chat_id = message['message']['chat']['id']
            txt = message['message']['text']
        elif "edited_message" in message:
            chat_id = message['edited_message']['chat']['id']
            txt = message['edited_message']['text']
        elif "inline_query":
            chat_id = message['inline_query']['from']['id']
            txt = message['inline_query']['query']

        if "/" in txt:
            command = txt.split(" ")[0].strip("/")
            args = [item for item in txt.split(" ")]
        else:
            command = None
            args = None

    except:
        chat_id = 801864779
        txt = "exception occured in parsing"
        command = None
        args = None
    return chat_id, txt, command, args


def tel_send_message(chat_id, text):
    url = f'https://api.telegram.org/bot{Token}/sendMessage'
    payload = {
        'chat_id': chat_id,
        'text': text
    }
    r = requests.post(url, json=payload)

    return r

def set_menu(chat_id):
    url = f'https://api.telegram.org/bot{Token}/setChatMenuButton'
    payload = {
        "chat_id": chat_id,
        "type": "commands"
    }
    r =  requests.post(url=url,json=payload)
    r.raise_for_status()
    return r.status_code


def tel_send_payment(chat_id):
    url = f'https://api.telegram.org/bot{Token}/sendInvoice'
    prices = [{"MRP": 15}, {"COST": 20}]
    price_json = json.dumps(prices)
    payload = {
        'chat_id': chat_id,
        'title': "Token for subs",
        'description': 'Great for you',
        'payload': "anything",
        'provider_token': "PLACE",
        'currency': "USD",
        "prices": price_json,

    }
    res = requests.post(url, json=payload)
    print(res.status_code)
    return res.raise_for_status()


def tel_send_poll(chat_id):
    url = f'https://api.telegram.org/bot{Token}/sendPoll'
    op = json.dumps(["superman", "batman"])

    payload = {
        "chat_id": chat_id,
        "question": "who wins?",
        "options": op
    }
    r = requests.post(url=url, json=payload)
    return r.status_code


@app.route("/", methods=['GET', 'POST'])
def home():
    db.create_all()
    if request.method == 'POST':
        msg = request.get_json()
        print(msg)
        chat_id, txt, command, args = tel_parse_message(msg)
        current_user = Users.query.filter_by(user_chat_id=chat_id).first()
        if not current_user:
            new_user = Users()
            new_user.user_name = request.json['message']['chat']['first_name']
            new_user.user_chat_id = chat_id
            new_user.credit = 200
            db.session.add(new_user)
            db.session.commit()
            set_menu(chat_id=chat_id)
            current_user = new_user
        if command is None:
            if txt == "hi":
                tel_send_message(chat_id, "Hello, world!")
            elif txt == "exception occured in parsing":
                tel_send_message(chat_id, txt)
            else:
                tel_send_message(chat_id, "nothing much")
        else:
            if command.title() == "Subscribe" or command.title() == "S":
                print(f"inside sub {args}")
                if current_user.credit >= MINCREDIT:
                    if args[1].title() == "Name":
                        query = " ".join(args[2:])
                        channel_in_db = Subscription.query.filter_by(channel_name=query).first()
                        flag = True
                    elif args[1].title() == "Id":
                        query = args[2]
                        channel_in_db = Subscription.query.get(query)
                        flag = False
                    else:
                        tel_send_message(chat_id, "command is incorrect")
                        return "Error", 200
                    if channel_in_db:
                        if current_user in channel_in_db.users:
                            tel_send_message(chat_id, "You are already subscriber.")
                        else:
                            current_user.subscriptions.append(channel_in_db)
                            current_user.credit -= 20
                            db.session.add(current_user)
                            db.session.commit()
                            tel_send_message(chat_id,
                                             f"You are added as subscriber.\nYour current credit is {current_user.credit}")
                    else:
                        if flag:
                            sel_channel_id = youtube_search_by_channel(query)
                        else:
                            sel_channel_id = query
                        if not (sel_channel_id == " " or sel_channel_id == "Error occurred. Search again"):
                            if subscribe(sel_channel_id) == 202:
                                new_sub = Subscription()
                                new_sub.channel_name = query
                                new_sub.channel_id = sel_channel_id
                                new_sub.users.append(current_user)
                                current_user.credit -= 20
                                db.session.add(new_sub)
                                db.session.add(current_user)
                                db.session.commit()
                                tel_send_message(chat_id, f"subscribed\nYour current credit is {current_user.credit}")
                        else:
                            print(sel_channel_id)
                            tel_send_message(chat_id, "Channel not found or error occurred while searching")
                else:
                    tel_send_message(chat_id, "You need at least 20 tokens for subscription. Use /reload for recharge.")
            if command.title() == "Credit":
                tel_send_message(chat_id, f"Your current credit is {current_user.credit}")
            if command.title() == "Reload":
                print(set_menu(current_user.user_chat_id))
        return Response('ok', status=200)
    else:
        return "Welcome"



@app.route("/feed/<channel_id>", methods=['GET', 'POST'])
def feed(channel_id):
    if request.method == 'GET':
        if request.args != {}:
            return request.args['hub.challenge']
        return "<h1>Hello<h1>"
    if request.method == "POST":
        data = request.data.decode()
        soup = BeautifulSoup(data, 'lxml')
        channel = str(soup.find("uri")).strip("<uri>").strip("</")
        video = youtube_video_base_url + str(soup.find("id")).strip("<id>").strip("</").split(":")[2]
        video_title = str(soup.find_all("title")[1]).strip("<title>").strip("</")
        name = str(soup.find("name")).strip("<name>").strip("</")
        # channel_id = channel.split("/")[-1]
        broadcast_channel = Subscription.query.get(channel_id)
        if broadcast_channel.channel_id == broadcast_channel.channel_name:
            broadcast_channel.channel_name = name
        print(f"{channel}{video}{video_title}{name}{channel_id}")
        for item in broadcast_channel.users:
            msg = f"Hey {item.user_name},\n{name} uploaded:\n{video_title}\ncheck that out from link below:\n{video}"
            tel_send_message(item.user_chat_id, msg)
        return "Success", 201


if __name__ == "__main__":
    app.run(debug=True)
