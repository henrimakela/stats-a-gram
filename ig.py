import requests
import time
import json
import datetime
from pymongo import MongoClient 
from pymongo.database import Database
from random import randint
from urllib.parse import quote
from dotenv import load_dotenv
import os
import config

load_dotenv()

def get_database():
    CONNECTION_STRING = os.environ["DB_URI"]
    client = MongoClient(CONNECTION_STRING)
    return client['ig']

def getAccountsThatDontFollowYouBack(followers, following):
    follower_usernames = list(map(lambda x: x.get('username'), followers))
    following_usernames = list(map(lambda x: x.get('username'), following))

    result = []

    for user in following_usernames:
        if user not in follower_usernames:
            result.append(user)
    return result


def refreshCollection(db: Database):
    collection_followers = db["followers"]
    followers = graphqlEndpoint(None)

    collection_followers.find_one_and_replace({},{
        "date": datetime.datetime.utcnow(),
        "followers": json.dumps(followers)
    })
    print("Followers refreshed")

def checkUnfollows(db: Database):
    collection_followers = db["followers"]
    followers = graphqlEndpoint(None)
    doc = collection_followers.find_one({})
    fstr = doc.get("followers")
    last_followers = json.loads(fstr) 
    print(last_followers)
    unfollows = []
    for follower in last_followers:
        if follower not in followers:
            unfollows.append(follower)
    print(unfollows)



def graphqlEndpoint(end_cursor, users=[], has_next_page = True ):
    time.sleep(randint(1,5))
    if has_next_page == False:
        return users

    payload = {

    } 

    payload['id'] = os.environ['IG_TARGET_ID']
    payload['first'] = "50"

    if end_cursor:
        payload['after'] = end_cursor

    payload_json = json.dumps(payload)
    encoded_payload = quote(payload_json)
    url = f"https://www.instagram.com/graphql/query/?query_hash=c76146de99bb02f6415203be841dd25a&variables=" + encoded_payload
    print(url)

    response = requests.get(url,cookies=config.cookies, headers=config.headers)
    data = response.json()
    entries = data['data']['user']['edge_followed_by']['edges']
    for entry in entries:
        users.append(entry['node']['username'])
    
    end_cursor = data['data']['user']['edge_followed_by']['page_info']['end_cursor']
    has_next_page = data['data']['user']['edge_followed_by']['page_info']['has_next_page']

    return graphqlEndpoint(end_cursor, users, has_next_page)

followers = graphqlEndpoint(None)