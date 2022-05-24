import copy
import requests
import json
import pickle
import sys
import random
import logging
import time
from datetime import datetime
from elasticsearch import Elasticsearch
from elasticsearch import ConnectionError, ConnectionTimeout, AuthenticationException, AuthorizationException, SerializationError, TransportError, RequestError, ElasticsearchWarning, NotFoundError
from instagrapi import Client, exceptions

'''
    python3 -m pip install instagrapi
    python3 -m pip install --upgrade Pillow
'''

class CannotIndexDocOnEs(Exception):
    '''Tweet\'s author and the found author don\'t match'''
    def __init__(self, message=''):
        super().__init__(message)

# initialize Elasticsearch
es_address='http://localhost:9200'
es = Elasticsearch(es_address)
list_accounts_to_verify = []
absolute_path = "/home/atrasacco/TikTokIG/"

settings = {
    "mapping": {
        "total_fields": {
            "limit": 2000
        }
    }
}

mappings = {
    "properties": {
        "sampled_timestamp": {
            "type": "date",
            "format": "date_optional_time"
        },
        "session_timestamp": {
            "type": "date",
            "format": "date_optional_time"
        }
    }
}

requests_counter = 0  # every n requests --> change account
ig_accounts = ["accountfortesting002", "accountfortesting04", "accountfortesting07", "accountfortesting08"]
ig_passwords = ["Andrea1234", "Andrea12", "Andrea1234", "Andrea12"]
errors_counter = [0, 0, 0, 0]
ig_index = 0 # index of current ig_account logged in
logged = False
ig_api = Client()

def IG_login():
    global requests_counter, logged, ig_index, ig_accounts, ig_passwords, ig_api
    requests_counter = 0
    ig_api.login(ig_accounts[ig_index], ig_passwords[ig_index])
    logged = True


def IG_logout():
    global ig_api, logged
    ig_api.logout()
    logged = False


def getIGFollowerCount(username, max_req_per_account=80, default_wait=6, variation=2, max_retry=3):
    global requests_counter, logged, ig_index, ig_accounts, ig_passwords, ig_api, list_accounts_to_verify
    if requests_counter == max_req_per_account and len(ig_accounts) > 1: # every 'max_req_per_account' --> change ig account (if there are 2 or more ig accounts)
        ig_index = (ig_index + 1) % len(ig_accounts)
        if logged:
            IG_logout()
    time.sleep(random.randint(default_wait - variation, default_wait + variation)) # wait between each (successful) request
    retry = -1
    login_attempt = -1
    ig_user = {"username_ig": username, "status": None}
    while retry < max_retry:
        retry += 1
        try:
            if not logged:
                IG_login()
            requests_counter += 1
            # user = ig_api.user_info_by_username(username)
            user = ig_api.user_info_by_username_v1(username)
            ig_user["status"] = "active"
            ig_user["social_id"] = user.pk
            ig_user["name"] = user.full_name
            ig_user["follower_count"] = user.follower_count
            ig_user["following_count"] = user.following_count
            ig_user["media_count"] = user.media_count
            break
        except exceptions.UserNotFound:
            ig_user["status"] = "not found"
            break
        except exceptions.ClientConnectionError as e:
            logger.error(e.message)
            time.sleep(20)
            if logged:
                ig_user["status"] = "unknown (connection error)"
                IG_logout()
        except exceptions.ChallengeError as e: # account error --> remove ig account
            logger.error(str(e.message) + " (USERNAME: " + str(username) + ", ACCOUNT: " + str(ig_accounts[ig_index]) + (", LOGIN_ERROR)" if not logged else ")"))
            list_accounts_to_verify.append(str(ig_accounts[ig_index]))
            ig_accounts.remove(ig_accounts[ig_index])
            del ig_passwords[ig_index]
            del errors_counter[ig_index]
            if ig_accounts is None or len(ig_accounts) == 0:
                sys.exit("ERROR! There are no more accounts to log in")
            ig_index = ig_index % len(ig_accounts)
            if logged:
                ig_user["status"] = "unknown (challenge error)"
                if len(ig_accounts) > 1:
                    IG_logout()
        except exceptions.PrivateError as e:
            logger.error(str(e.message) + " (USERNAME: " + str(username) + ", ACCOUNT: " + str(ig_accounts[ig_index]) + (", LOGIN_ERROR)" if not logged else ")"))
            ig_index = (ig_index + 1) % len(ig_accounts) # step to next account
            if logged:
                ig_user["status"] = "unknown (" + e.message + ")"
                if len(ig_accounts) > 1:
                    IG_logout()
        except exceptions.ClientJSONDecodeError as e:
            logger.error("Json decode error; " + " (USERNAME: " + str(username) + ", ACCOUNT: " + str(ig_accounts[ig_index]) + (", LOGIN_ERROR)" if not logged else ")"))
            ig_user["status"] = "unknown (json decode error)"
            break
        except exceptions.ClientError as e:
            logger.error(str(e.message) + " (USERNAME: " + str(username) + ", ACCOUNT: " + str(ig_accounts[ig_index]) + (", LOGIN_ERROR)" if not logged else ")"))
            if logged:
                ig_user["status"] = "unknown (" + e.message + ")"
                if len(ig_accounts) > 1:
                    IG_logout()
            else:
                errors_counter[ig_index] += 1
                if errors_counter[ig_index] == 10:
                    ig_accounts.remove(ig_accounts[ig_index])
                    del ig_passwords[ig_index]
                    del errors_counter[ig_index]
                    if ig_accounts is None or len(ig_accounts) == 0:
                        sys.exit("ERROR! There are no more accounts to log in")
                    ig_index = ig_index % len(ig_accounts)
                    continue
            if e.message == "checkpoint_required":
                ig_index = (ig_index + 1) % len(ig_accounts)
            elif e.code == 500:  # Internal Server Error
                time.sleep(300)  # wait 5 minutes
        except Exception as e:
            logger.error(str(e))
            time.sleep(20)
            if logged:
                IG_logout()
        time.sleep(default_wait * 2) # wait before the next attempt
    return ig_user

from TikTokApi import TikTokApi
api = TikTokApi(custom_verify_fp="verify_l0tdebqo_wEeXVUpb_eCCU_4aZj_9Chs_1pajcqN7iGCE", sid_tt="ac56b1a2db48c4329b8268ee09c30bef")#,

def setup_logger(logger_name, log_file, level=logging.INFO):
    l = logging.getLogger(logger_name)
    l.setLevel(level)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler = logging.FileHandler(log_file, mode='w')
    handler.setFormatter(formatter)
    l.addHandler(handler)

def save_pickle(obj, path, filename):
    with open(path + filename + '.pkl', 'wb') as output:
        pickle.dump(obj, output, pickle.HIGHEST_PROTOCOL)


def load_pickle(path, filename):
    with open(path + filename + '.pkl', 'rb') as input:
        obj= pickle.load(input)
        return obj

setup_logger('execution_log', absolute_path + 'execution.log')
logger = logging.getLogger('execution_log')

# create index
def initialize_index(settings, mappings, index_name):
    # Inizializzo indice Elastic con mapping
    try:
        logger.info(f'Creating Elasticsearch index \'{index_name}\' if it doesn\'t exist...')
        es.indices.create(
            index=index_name,
            settings=settings,
            mappings=mappings
        )
        logger.info(f'Created and mapped the Elasticsearch index \'{index_name}\'')
        return True
    except RequestError as re:
        logger.warning(f'Index \'{index_name}\' already exists: {str(re)}')
        return True
    except ElasticsearchWarning as err:
        logger.info(f'initialize_index - initialize_index(): Cannot create Elasticsearch index \'{index_name}\': {str(err)}. Caused by: {str(err)}')
        return False


def index_doc(index_name, tt_user, id_doc=None, upload_username_IG=False):
    retry = 3
    done = False
    while not done and retry > 0:
        try:
            info_to_insert = tt_user
            if upload_username_IG:
                id_doc = str(tt_user['uid'])

                info_to_insert = {
                    'uid_TK': tt_user["uid"],
                    'username_IG': tt_user.get('ins_id')
                }
            response = es.index(index=index_name, id=id_doc, document=info_to_insert, refresh=True)
            done = True
            if response.get('body') and response['body'].get('result') != 'created':
                message = f'ES response for user {tt_user} is: {response}'
                raise CannotIndexDocOnEs(message)
            return response
        except (ConnectionTimeout, ConnectionError, AuthenticationException, AuthorizationException, SerializationError,                TransportError) as ce:
            logger.info(f'ESUtils - index_doc() - Elasticsearch connection error: {str(ce)}. Terminating.')
            retry -= 1
            if retry <= 0:
                raise ce
        except Exception as e:
            logger.info(f'ESUtils - index_doc(): {str(e)}')
            retry -= 1
            if retry <= 0:
                raise e

    if not done:
        message = f'Coudln\'t index user: {tt_user}'
        raise CannotIndexDocOnEs(message)

def get_username_IG(index_name, user_id, user_name):
    # return status, username_IG
    try:
        username_IG = None
        body = {
            "term": {
                "_id": {
                    "value": str(user_id)
                }
            }
        }
        response = es.search(index=index_name, query=body)
        hits = response["hits"]["hits"]
        if len(hits) == 1:
            username_IG = hits[0]['_source']['username_IG']

        return True, username_IG
    except Exception as e:
        logger.info(f'Exception if get_username_IG for tt_user {user_id}, {user_name}')
        return False, None

def default_variable(data={}):
    items = {}
    items['app_language'] = "en" #cs
    #items['language'] = "it"
    #items['region'] = "it"
    #items['app_type'] = "normal"
    #items['sys_region'] = "IT"
    #items['carrier_region'] = "IT"
    #items['carrier_region_v2'] = "230"
    items['build_number'] = "10.3.3"
    #items['timezone_offset'] = "10800"
    #items['timezone_name'] = "Europe/Istanbul"
    #items['mcc_mnc'] = "23001"
    #items['is_my_cn'] = "0"
    #items['fp'] = ""
    #items['account_region'] = "IT"
    #items['iid'] = "6620659482206930694"
    #items['ac'] = "wifi"
    items['channel'] = "googleplay"
    items['aid'] = "1233"
    items['app_name'] = "musical_ly"
    items['version_code'] = "100303"
    items['version_name'] = "10.3.3"
    #    items['device_id'] = "6594726280552547846"
    items["device_id"] = str(random.randint(1000000000000000000, 9999999999999999999))
    items['device_platform'] = "android"
    # items['ssmix'] = "a"
    items['device_type'] = "Pixel"
    items['device_brand'] = "Google"
    #items['os_api'] = "26"
    items['os_version'] = "9.0.0"
    #items['openudid'] = "b307b864b574e818"
    #items['manifest_version_code'] = "2019011531"
    #items['resolution'] = "720*1280"
    #items['dpi'] = "320"
    #items['update_version_code'] = "2019011531"
    #items['_rticket'] = int(round(time.time() * 1000))
    #items['ts'] = int(round(time.time() * 1000))
    #items['as'] = "a145cac75e153c5ef36066"
    #items['cp'] = "ab5ac054ec3175e3e1Yaae"
    # items['mas'] = "016d48633d67d491135bc9b025d80be9d56c6c0c6ccc66a6acc6cc"
    # qui https://github.com/LCSP/tiktokapi-security c'è scritto che probabilmente il mas non importa se vogliamo solamente raccogliere info (GET)
    if len(data) > 0:
        for x, y in data.items():
            items[x] = y
    return items


session = requests.session()
#session.proxies['http'] = 'http://contabo10.int.wevo.it:3130'
#session.proxies['https'] = 'https://contabo10.int.wevo.it:3130'

'''
https://github.com/tolgatasci/musically-tiktok-api-python/blob/master/api.py

Followers list endpoint: https://api2.musical.ly/aweme/v1/user/follower/list/?user_id=<USER_ID>&count=20&retry_type=no_retry
'''

headers_musically = {
    "User-Agent": "okhttp",
    #'host': 'api2.musical.ly',
    #'X-SS-TC': "0",
    #'User-Agent': "com.zhiliaoapp.musically/2018090613 (Linux; U; Android 8.0.0; tr_TR; TA-1020; Build/O00623; Cronet/58.0.2991.0)",
    #'Accept-Encoding': "gzip",
    #'Connection': "keep-alive",
    #'X-Tt-Token': "",
    #'sdk-version': "1",
    #'Cookie': ''
}


dict_users = load_pickle(absolute_path, "id_users")
list_usernames = list(dict_users.values())

params_musically_template = {
    'cursor': '0',
    'keyword': "",
    'count': '10',
    'type': '1',
    'hot_search': '0',
    'search_source': 'discover'
}


url_musically = 'https://api-t2.tiktokv.com/aweme/v1/discover/search/'
list_infos = list()

count = 0
banned_words = {
    'bulimia': 'bulim',
    'bulimi': 'bulim',
    'overdose': 'overdos',
    'self-harm': 'self-har',
    'suicide': 'suicid',
    'sexy': 'sex',
    'anoressia': 'anoressi',
    'penis': 'peni',
    'vagina': 'vagin',
    'replica': 'replic',
    'pornographie': 'pornograph',
    'pornography': 'pornograph',
    'porno': 'por',
    'porn': 'por',
    'anorexia': 'an',
    'anorexi': 'an',
    'anorex': 'an',
    'anore': 'an',
    'anor': 'an',
    'ano': 'an',
    'weed': 'wee',
    "oui’d": "oui'",
    'hitler': 'hitle',
    'cock': 'coc',
    'cocksucker': 'cocksucke',
    'dickhead': 'dic',
    'dick': 'dic',
    'lickmyass': 'lickmyas',
    'pussy': 'puss',
    'tits': 'tit',
    'boobs': 'boo',
    'boob': 'boo',
    'whore': 'whor'


}


def handle_banned_words(params_musically, user_name):
    for word, new_word in banned_words.items():
        if word in user_name.lower():
            params_musically['keyword'] = user_name.lower().replace(word, new_word)
    return params_musically


def check_username(params_musically, user_id, user_name):
    logger.info(f"checking if username {user_name} with userID {user_id} changed")
    try:
        user = api.user(user_id=user_id).info_full()
    except KeyError as ke:
        if str(ke) == 'userMap':
            logger.info('user cannot be found with davidtheatre.')
        else:
            logger.info(f'generic error in davidtheatre API: {str(ke)}')
        return params_musically, user_name, False, True, False
    new_user_name = user_name
    if not user:
        logger.info(f'user with userID {user_id} cannot be found neither with davidtheatre')
        return params_musically, new_user_name, False, True, False
    changed_username = False
    if user[user_id]["uniqueId"] != user_name:
        changed_username = True
        logger.info(
            f"user with ID: {user_id} changed username from: {user_name} to {user[user_id]['uniqueId']}")
        new_user_name = user[user_id]["uniqueId"]
        params_musically["keyword"] = new_user_name
        params_musically = handle_banned_words(params_musically, new_user_name)
    deleted_TikToker = False if user[user_id]['nickname'] != 'Tik Toker' else True
    if not changed_username:
        logger.info(f'cannot retrieve info for user: {user_name}')
        return params_musically, new_user_name, False, False, deleted_TikToker
    params_musically["cursor"] = "0"
    return params_musically, new_user_name, True, False, deleted_TikToker


def tiktok_info(user_name, user_id):
    global count
    go_on = False
    response = None
    count_change_device_id = 0
    found = False
    infos = dict()
    deleted = False
    deleted_TikToker = False
    username_change_checked = False
    params_musically = copy.deepcopy(params_musically_template)
    sampling_timestamp = None

    try:
        while not go_on:
            params_musically['keyword'] = user_name
            params_musically = handle_banned_words(params_musically, user_name)
            params_musically.update(default_variable())
            end_pagination = False
            found = False
            infos = dict()
            while not found and not end_pagination:
                response = session.get(url_musically, params=params_musically, headers=headers_musically)
                j = json.loads(response.text)
                if j.get('status_msg') == 'Accedi prima col tuo account' or j.get('status_msg') == 'Oops, il tuo account è stato temporaneamente sospeso.' \
                        or not j.get('user_list'):
                    params_musically['device_id'] = str(random.randint(1000000000000000000, 9999999999999999999))
                    logger.info(f"new_device_id: {params_musically['device_id']} ")
                    count_change_device_id += 1
                    if count_change_device_id == 20:
                        if not username_change_checked:
                            params_musically, user_name, changed_username, deleted, deleted_TikToker = check_username(params_musically, user_id,
                                                                                                                      user_name)
                            username_change_checked = True
                            if changed_username:
                                count_change_device_id = 0
                            else:
                                break
                        else:
                            logger.info(f'Username change already checked. No more data about this user {user_id}, '
                                        f'{user_name}')
                            break
                    continue
                for user in j['user_list']:
                    #infos = user['user_info']
                    if user['user_info']['uid'] == user_id:
                        found = True
                        infos = user['user_info']
                        sampling_timestamp = datetime.now().isoformat()
                        break
                params_musically['cursor'] = j['cursor']
                end_pagination = True if not j.get('has_more') else False
            if not found:
                if not username_change_checked:
                    params_musically, user_name, changed_username, deleted, deleted_TikToker = check_username(params_musically, user_id, user_name)
                    username_change_checked = True
                    if changed_username:
                        continue
                    else:
                        logger.info(f'scrolled everything. last_uid: {infos["uid"]}, user_info: {user_id}')
                else:
                    logger.info(f'username change already checked. Scrolled everything. last_uid: {infos["uid"]}, '
                                f'user_info: {user_id}')
            #                sys.exit(-1)
            else:
                list_infos.append(infos)
                save_pickle(list_infos, absolute_path, 'list_user_infos')
                count += 1
                if count % 100 == 0:
                    logger.info(f"#users:{count} ")
            go_on = True
        infos["deleted"] = deleted
        infos["deleted_Tiktoker"] = deleted_TikToker
        return infos, found
    except Exception as e:
        logger.error(f"exception: {str(e)} ")
        if response:
            logger.info(f"response.txt: {response.text}")
        logger.info(f"current_username: {user_name}")
        infos["deleted"] = deleted
        infos["deleted_Tiktoker"] = deleted_TikToker
        return infos, found


def main_info():
    global list_accounts_to_verify
    # create ES index
    index_name = 'tt_users_official'
    intialized = initialize_index(settings, mappings, index_name)
    if not intialized:
        sys.exit(-1)

    id = 0
    session_timestamp = datetime.now().isoformat()
    ig_accounts_to_verify = dict()
    ig_accounts_to_verify["date"] = session_timestamp
    logger.info(f'session_timestamp: {session_timestamp}')
    for user_id, user_name in dict_users.items():
        if id == 5000:
            break
        id += 1
        logger.info(f'==================================')
        infos = {"session_timestamp": str(session_timestamp)}
        logger.info(f'Retrieving TikTok info of {user_name}, {user_id}')
        tt_infos, found = tiktok_info(user_name, user_id)
        logger.info(f'Retrieved TikTok info of {user_name}, {user_id}')
        username_IG = tt_infos.get('ins_id')
        ig_infos = None
        if username_IG is None or username_IG == "":
            done, username_IG = get_username_IG("usernames_ig", user_id, user_name)
        else:
            done = True
        if done and username_IG:
            logger.info(f'Need to retrieve followers of {username_IG}')
            ig_infos = getIGFollowerCount(username_IG)
            logger.info(f'Retrieved IG followers of {username_IG}')

        infos["sampled_timestamp"] = str(datetime.now().isoformat()) # SAMPLED TIMESTAMP
        logger.info(f'Sampled timestamp: {infos["sampled_timestamp"]}')
        if found:
            try:
                infos["Tiktok"] = tt_infos
                infos["Instagram"] = ig_infos
                response = index_doc(index_name, infos)
                logger.info('TikTok info found: loaded on ES')
            except Exception as e:
                logger.info(str(e))
                # chiedere a Maurizio cosa fare, per il momento continuiamo
        else:
            try:
                tt_infos = dict()
                tt_infos['uid'] = user_id
                tt_infos['unique_id'] = user_name
                infos["Tiktok"] = tt_infos
                infos["Instagram"] = ig_infos
                response = index_doc(index_name, infos)
                logger.info('TikTok info NOT found, loaded on ES')
            except Exception as e:
                logger.info(str(e))
    ig_accounts_to_verify["ig_accounts"] = list_accounts_to_verify
    json_object = json.dumps(ig_accounts_to_verify, indent=4)
    outfile = open(absolute_path + "ig_accounts_to_verify.json", "w")
    outfile.write(json_object)
    outfile.close()


def load_username_IG_on_ES():
    index_name = 'usernames_ig'
    #TODO: recuperare lista di utenti tiktok (tt_user) dal file list_user_infos.pkl, usando il metodo load_pickle(
    # "./", "list_user_infos.pkl")
    tt_users = load_pickle(absolute_path, "list_user_infos")
    # inizializzo indice per username_IG
    initialize_index(settings, mappings, index_name)

    #TODO: ciclare su tt_users:
    for tt_user in tt_users:
        username = tt_user.get('ins_id')
        if username is not None and not username == "":
            response = index_doc(index_name, tt_user, None, upload_username_IG=True)
            logger.info(f'Response from indexing tt_user {tt_user["uid"]}')

if __name__ == '__main__':
    main_info()
    #load_username_IG_on_ES()