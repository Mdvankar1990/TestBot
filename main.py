import os
import requests
from bs4 import BeautifulSoup
from flask import Flask, request, Response
from flask_sqlalchemy import SQLAlchemy
from telebot import TeleBot

from pubsub import youtube_search_by_channel, subscribe

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['DATABASE']
db = SQLAlchemy(app)
Token = os.environ["TELE_Token"]
bot = TeleBot(Token, parse_mode=None)
bot.remove_webhook()
op = bot.set_webhook(url=os.environ['BASE_URL'])
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


def tel_parse_message(message):
    # print("message-->", message)

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
    # print("chat_id-->", chat_id)
    # print("txt-->", txt)
    # print("command-->", command)
    # print("args-->", args)
    return chat_id, txt, command, args


def tel_send_message(chat_id, text):
    url = f'https://api.telegram.org/bot{Token}/sendMessage'

    payload = {
        'chat_id': chat_id,
        'text': text
    }
    r = requests.post(url, json=payload)

    return r
def tel_send_payment():
    pass


@app.route("/", methods=['GET', 'POST'])
def home():
    db.create_all()
    print(request.method)
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
            current_user = new_user
        print(chat_id)
        if command is None:
            if txt == "hi":
                tel_send_message(chat_id, "Hello, world!")
            else:
                tel_send_message(chat_id, 'Nothing much')
        else:
            if command.title() == "Subscribe" or command.title() == "S":
                print(args[1].title())
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
                                         "You are added as subscriber.\nYour current credit is {current_user.credit}")
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
            if command.title() == "Credit":
                tel_send_message(chat_id, f"Your current credit is {current_user.credit}")

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
        video_id = str(soup.find("id")).strip("<id>").strip("</").split(":")[2]
        video_title = str(soup.find_all("title")[1]).strip("<title>").strip("</")
        name = str(soup.find("name")).strip("<name>").strip("</")
        broadcast_channel = Subscription.query.get(channel_id)
        if broadcast_channel.channel_id == broadcast_channel.channel_name:
            broadcast_channel.channel_name = name
        print(f"{channel}{video_id}{video_title}{name}{channel_id}")
        for item in broadcast_channel.users:
            msg = f"Hey {item.user_name},\n{name} have {video_title} check that out from link below:\n{channel}"
            tel_send_message(item.user_chat_id, msg)
        return "Success", 201


if __name__ == "__main__":
    app.run(debug=True)
