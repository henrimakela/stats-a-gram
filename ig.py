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


def refreshCollection(id, headers, db: Database):
    print("Refreshing collection")
    collection_followers = db[str(id)]["followers"]

    headers = {
        'cookie':config['cookie']
    }

    followers = getFollowers(id, headers, None)

    collection_followers.update_one({},{'$set':{
        "date": datetime.datetime.utcnow(),
        "followers": json.dumps(followers)
    }}, upsert=True)

    print("Followers refreshed")

def getDailyData(id, config, db: Database):
    collection_followers = db[str(id)]["followers"]
    if collection_followers.find_one({}) is None:
        print("No previous data found. Jumping out...")
        return

    headers = {
        'cookie':config['cookie']
    }

    followers = getFollowers(id, headers, None)

    print("Fetching previous day from the db..")
    doc = collection_followers.find_one({})
    fstr = doc.get("followers")
    last_followers = json.loads(fstr) 
    unfollowers = []
    new_followers = []
    print("Comparing")
    for follower in last_followers:
        if follower not in followers:
            unfollowers.append(follower)

    for follower in followers:
        if follower not in last_followers:
            new_followers.append(follower)
    count = len(followers)
    
    print(count)
    collection_other = db[str(id)]["other"]
    collection_other.insert_one({
        "date": datetime.datetime.utcnow(),
        "unfollowers": unfollowers,
        "new_followers": new_followers,
        "follower_count": count
    })
    print("Get daily data finished")



def getFollowers(id, headers, end_cursor, users=[], has_next_page = True ):
    time.sleep(randint(1,5))
    print("Fetching followers...")
    if has_next_page == False:
        return users

    payload = {

    } 

    payload['id'] = id
    payload['first'] = "50"

    if end_cursor:
        payload['after'] = end_cursor

    payload_json = json.dumps(payload)
    encoded_payload = quote(payload_json)
    url = f"https://www.instagram.com/graphql/query/?query_hash=c76146de99bb02f6415203be841dd25a&variables=" + encoded_payload

    response = requests.get(url, headers=headers)
    data = response.json()
    entries = data['data']['user']['edge_followed_by']['edges']
    for entry in entries:
        users.append(entry['node']['username'])
    
    end_cursor = data['data']['user']['edge_followed_by']['page_info']['end_cursor']
    has_next_page = data['data']['user']['edge_followed_by']['page_info']['has_next_page']

    return getFollowers(id, headers, end_cursor, users, has_next_page)


def fetchTarget(id, config, db):
    getDailyData(id, config, db)
    refreshCollection(id, config, db) 

db = get_database()
config = db['config'].find_one()
targetList = json.loads(os.environ['IG_TARGET_LIST'])

for targetId in targetList:
    fetchTarget(targetId, config, db)
