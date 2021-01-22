import json
import os
import re
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import as_completed

import requests

from header_config import login_header
from langconv import *
from utils import count_time

proxies = {
    'http': 'http://127.0.0.1:10800',
    'https': 'https://127.0.0.1:10800',
}


class TwitterDownload():
    base_url = 'https://api.twitter.com/2/timeline/media/{}.json'
    member_list_url = 'https://api.twitter.com/1.1/lists/members.json?include_profile_interstitial_type=1&include_blocking=1&include_blocked_by=1&include_followed_by=1&include_want_retweets=1&include_mute_edge=1&include_can_dm=1&include_can_media_tag=1&skip_status=1&cards_platform=Web-12&include_cards=1&include_composer_source=true&include_ext_alt_text=true&include_reply_count=1&tweet_mode=extended&count=1000&list_id={}'
    member_list_id_api = 'https://api.twitter.com/1.1/lists/ownerships.json?include_profile_interstitial_type=1&include_blocking=1&include_blocked_by=1&include_followed_by=1&include_want_retweets=1&include_mute_edge=1&include_can_dm=1&include_can_media_tag=1&skip_status=1&cards_platform=Web-12&include_cards=1&include_composer_source=true&include_ext_alt_text=true&include_reply_count=1&tweet_mode=extended&cursor=-1&user_id={}'
    followed_api = 'https://api.twitter.com/graphql/bVnpAjMS0oiPz0VO79k9xQ/Following?variables={}'
    user_id_api = 'https://api.twitter.com/graphql/-xfUfZsnR_zqjFd-IfrN5A/UserByScreenName?variables=%7B%22screen_name%22%3A%22{}%22%2C%22withHighlightedLabel%22%3Atrue%7D'
    main_user_name_api = 'https://api.twitter.com/graphql/P8ph10GzBbdMqWZxulqCfA/UserByScreenName?variables=%7B%22screen_name%22%3A%22{}%22%2C%22withHighlightedLabel%22%3Atrue%7D'
    backup_user_name_api = 'https://api.twitter.com/graphql/-xfUfZsnR_zqjFd-IfrN5A/UserByScreenName?variables=%7B%22screen_name%22%3A%22{}%22%2C%22withHighlightedLabel%22%3Atrue%7D'
    general_save_path = r'E:\爬虫\twitter'
    member_save_path = r'E:\爬虫\twitter_members'
    headers = login_header
    repeat_pattern = '_\d{18,20}.*'

    # copy from chrome
    tweets_params = {
        'include_profile_interstitial_type': '1',
        'include_blocking': '1',
        'include_blocked_by': '1',
        'include_followed_by': '1',
        'include_want_retweets': '1',
        'include_mute_edge': '1',
        'include_can_dm': '1',
        'include_can_media_tag': '1',
        'skip_status': '1',
        'cards_platform': 'Web-12',
        'include_cards': '1',
        'include_ext_alt_text': 'true',
        'include_quote_count': 'true',
        'include_reply_count': '1',
        'tweet_mode': 'extended',
        'include_entities': 'true',
        'include_user_entities': 'true',
        'include_ext_media_color': 'true',
        'include_ext_media_availability': 'true',
        'send_error_codes': 'true',
        'simple_quoted_tweet': 'true',
        'count': '10000',
        'ext': 'mediaStats,highlightedLabel',
    }

    def __init__(self, user_name=None, ):
        self.user_name = user_name
        self.member_screen_name_list = [member.get('screen_name') for member in self.get_member_list(user_name)]

    # @count_time
    def get_tweets(self, user_id):
        for i in range(1, 5):
            try:
                url = self.base_url.format(user_id)
                res = requests.get(url=url, proxies=proxies, headers=self.headers, params=self.tweets_params,
                                   timeout=i * 30)
                if res.status_code != 200:
                    print(res.json())
                    return {}
                tweets = res.json().get('globalObjects').get('tweets')
            except Exception as e:
                # print("get_tweets fail:%s\ntraceback:%s" % (user_id, traceback.format_exc()))
                print("get_tweets fail:%s\nException:%s" % (user_id, e))
                time.sleep(i * 30)

            else:
                return tweets

    # @count_time
    def get_user_id(self, user_name):
        for i in range(1, 5):
            try:
                response = requests.get(self.user_id_api.format(user_name),
                                        proxies=proxies, timeout=i * 30,
                                        headers=login_header).json()
                user_id = response['data']['user']['rest_id']
            except Exception as e:
                print('get_user_id fail:%s-times:%s,exception:%s' % (user_name, i, e))
                time.sleep(i * 10)
            else:
                print('{}:get_user_id success:{}'.format(user_name, user_id))
                return user_id

    def rename_repeat_file(self, save_dir, legal_file_name):
        try:
            post_file_name = re.search(self.repeat_pattern, legal_file_name).group()
            file_list = os.listdir(save_dir)
            for file in file_list:
                res = re.search(self.repeat_pattern, file)
                if not res:
                    continue
                post_del_file_name = res.group()
                if file != legal_file_name and post_file_name == post_del_file_name:
                    src_file_path = os.path.join(save_dir, file)
                    dst_file_path = os.path.join(save_dir, legal_file_name)
                    print(file)
                    print(legal_file_name)
                    if os.path.exists(dst_file_path):
                        os.remove(src_file_path)
                    else:
                        os.rename(src_file_path, dst_file_path)
        except Exception as e:
            print('legal_file_name:{},Exception:{}'.format(legal_file_name, e))

    def save_file(self, download_url, save_dir, legal_file_name):
        self.rename_repeat_file(save_dir, legal_file_name)
        file_path = os.path.join(save_dir, legal_file_name)
        if os.path.exists(file_path):
            return
        for i in range(5):
            try:
                content = requests.get(download_url, timeout=(i + 1) * 60, proxies=proxies).content
                file_path = os.path.join(save_dir, legal_file_name)
                with open(file_path, 'wb') as f:
                    f.write(content)
            except Exception:
                print("save_file fail:%s\ntraceback:%s" % (download_url, traceback.format_exc()))
            else:
                print(file_path)
                return

    def get_save_dir(self, unique_username):
        dir_list = os.listdir(self.save_path)
        for dir in dir_list:
            if unique_username in dir:
                return dir

    def get_max_video_url(self, media):
        try:
            variants = media['video_info']['variants']
            variants_video = [variant for variant in variants if variant.get('bitrate') != None]
            sort_variants_video = sorted(variants_video, key=lambda x: x.get('bitrate'))
            max_video_url = sort_variants_video[-1]['url']
        except Exception:
            print("get_max_video_url fail:%s\ntraceback:%s" % (media, traceback.format_exc()))
        else:
            return max_video_url

    # @count_time
    def rename_twitter(self, download_url, save_dir, legal_save_name, id_str):
        file_path = os.path.join(save_dir, legal_save_name)
        new_file_name = id_str + "____" + legal_save_name
        new_file_path = os.path.join(save_dir, new_file_name)
        if os.path.exists(file_path):
            os.rename(file_path, new_file_path)
            print(new_file_path)

    def get_legal_file_name(self, tweet):
        id_str = tweet['id_str']
        full_text = tweet['full_text']
        full_text = full_text.split('http')[0]
        full_text = re.sub('#\w+', '', full_text)
        # full_text = re.sub('@\w+', '', full_text)
        full_text = re.sub(r"[^\w@]", "", full_text)
        full_text = Converter('zh-hans').convert(full_text)
        legal_file_name = full_text.strip()[:150]
        return legal_file_name or id_str

    def dowload_one_twitter(self, tweet, save_dir):
        try:
            extended_entities = tweet.get('extended_entities')
            if not extended_entities:
                return
            id_str = tweet['id_str']
            legal_file_name = self.get_legal_file_name(tweet)
            media_list = extended_entities['media']
            for index, media in enumerate(media_list):
                video_info = media.get('video_info')
                type = media.get('type')
                if video_info:
                    download_url = self.get_max_video_url(media)
                    file_size = download_url.split('vid/')[-1].split('/')[0]
                    # file_size=re.match('(.*)(\d{3,4}x\d{3,4})(.*)',download_url).group(1)
                    file_format = '.mp4'
                    if type != 'animated_gif':
                        legal_save_name = legal_file_name + '_' + id_str + '_' + file_size + file_format
                    else:
                        legal_save_name = legal_file_name + '_' + id_str + file_format

                else:
                    img_url = media['media_url']
                    download_url = img_url.split('.jpg')[0] + '?format=jpg&name=large'
                    file_format = '.jpg'
                    legal_save_name = legal_file_name + '_' + id_str + '_' + str(index) + file_format

                self.save_file(download_url, save_dir, legal_save_name)
        except Exception:
            print("dowload_one_twitter fail:%s\ntraceback:%s" % (tweet, traceback.format_exc()))

    # @count_time
    def download_all_twitter(self, tweets, unique_name, user_name):
        if unique_name in self.member_screen_name_list:
            self.save_path = self.member_save_path
        else:
            self.save_path = self.general_save_path
        save_dir_name = self.get_save_dir(unique_name)
        if save_dir_name:
            save_dir = os.path.join(self.save_path, save_dir_name)
        else:
            save_dir = os.path.join(self.save_path, user_name + '_' + unique_name)
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)
            print('makedirs:%s' % save_dir)
        # with ThreadPoolExecutor(max_workers=1) as executor:
        with ThreadPoolExecutor() as executor:
            t_dict = {executor.submit(self.dowload_one_twitter, tweet, save_dir): tweet for tweet in tweets.values()}
            for future in as_completed(t_dict):
                tweet = t_dict[future]
                try:
                    future.result()
                except Exception:
                    print('download异常:%s' % tweet + '\n', traceback.format_exc())

    @count_time
    def get_member_list(self, user_name):
        user_id = self.get_user_id(user_name)
        try:
            response = requests.get(url=self.member_list_id_api.format(user_id),
                                    proxies=proxies,
                                    headers=self.headers,
                                    timeout=60).json()
            member_list_id = response['lists'][0]['id_str']
            res = requests.get(url=self.member_list_url.format(member_list_id),
                               proxies=proxies,
                               headers=self.headers,
                               timeout=60).json()
            members = res['users']
        except Exception:
            print("get_member_list fail:%s\ntraceback:%s" % (user_name, traceback.format_exc()))
        else:
            print('members:%s' % len(members))
            return members

    @count_time
    def get_all_followed(self, user_name):
        # variables = {"count": 1000, "withHighlightedLabel": False, "includePromotedContent": False}
        variables = {"count": 200, "withHighlightedLabel": False,
                     "withTweetQuoteCount": False, "includePromotedContent": False, "withTweetResult": False,
                     "withUserResult": False}

        user_id = str(self.get_user_id(user_name))
        variables['userId'] = user_id

        # unquote_url = unquote(followed_api)
        all_user_entries_list = []
        while True:
            try:
                variables_str = json.dumps(variables)
                res = requests.get(url=self.followed_api.format(variables_str), proxies=proxies, headers=login_header,
                                   timeout=60).json()
                all_user_entries = res['data']['user']['following_timeline']['timeline']['instructions'][-1]['entries']
            except Exception:
                print("get_all_followed fail:%s\ntraceback:%s" % (user_name, traceback.format_exc()))
                # print(res)
                time.sleep(30)
            else:
                if len(all_user_entries) <= 2:
                    break
                cursor = all_user_entries[-2]['content']['value']
                variables["cursor"] = cursor
                all_user_entries_list.extend(all_user_entries[:-2])
        print('get_all_followed:%s' % len(all_user_entries_list))
        return all_user_entries_list

    # @count_time
    def get_user_name(self, screen_name):
        try:

            urls = [self.main_user_name_api, self.backup_user_name_api]
            for url in urls:
                url = url.format(screen_name)
                res = requests.get(url, proxies=proxies, timeout=60, headers=self.headers).json()
                if res.get('data'):
                    username = res['data']['user']['legacy']['name']
                    break
            else:
                username = ''
        except Exception:
            print("get_user_name fail:%s\ntraceback:%s" % (screen_name, traceback.format_exc()))
            username = screen_name
        # legal_user_name = re.sub(r"[\/\\\:\*\?\"\<\>\|!！\.\s]", "", username)
        legal_user_name = re.sub(r"[^\w]", "", username)
        legal_user_name = Converter('zh-hans').convert(legal_user_name)
        if not legal_user_name:
            legal_user_name = screen_name
        return legal_user_name

    @count_time
    def download_oneuser(self, screen_name):
        user_id = self.get_user_id(screen_name)
        if not user_id:
            print('获取user_id失败:{}'.format(screen_name))
            return
        user_name = self.get_user_name(screen_name)
        tweets = self.get_tweets(user_id)
        if not tweets:
            print('获取推特为空:{}'.format(screen_name))
            return
        self.download_all_twitter(tweets, screen_name, user_name)

    @count_time
    def download_member_list(self, username=None):
        username = username or self.user_name
        members = self.get_member_list(username)
        for member in members:
            screen_name = member.get('screen_name')
            user_name = member.get('name')
            print('user_name:%s----screen_name:%s' % (user_name, screen_name))
            self.download_oneuser(screen_name)

    def rename_dir(self, unique_name, user_name):
        old_save_dir = os.path.join(self.save_path, user_name)
        if not os.path.exists(old_save_dir):
            return
        new_save_dir = os.path.join(self.save_path, user_name + '_' + unique_name)
        os.rename(old_save_dir, new_save_dir)

    @count_time
    def download_followed(self, user_name=None):
        user_name = user_name or self.user_name
        all_followed = self.get_all_followed(user_name)
        # all_followed.reverse()
        # random.shuffle(all_followed)
        for index, follow in enumerate(all_followed):
            try:
                followed_screen_name = follow['content']['itemContent']['user']['legacy']['screen_name']
                followed_user_name = self.get_user_name(followed_screen_name)
                followed_user_id = follow['content']['itemContent']['user']['rest_id']
                tweets = self.get_tweets(followed_user_id)
            except Exception:
                print("all_followed fail:%s\ntraceback:%s" % (follow, traceback.format_exc()))
                time.sleep(30)
            else:
                if not tweets:
                    print('tweets is None:%s' % followed_screen_name)
                    time.sleep(60)
                    continue
                if followed_screen_name in self.member_screen_name_list:
                    continue
                self.download_all_twitter(tweets, followed_screen_name, followed_user_name)
                # self.rename_dir(followed_screen_name, legal_followed_user_name)
            finally:
                print('finish:%s' % (index))
            # time.sleep(60)download_all_twitter

    def download_followed_depth(self, user_name, depth):
        all_followed = self.get_all_followed(user_name)
        if depth == 0:
            all_followed_screen_name = []
            for followed in all_followed:
                try:
                    screen_name = followed['content']['itemContent']['user']['legacy']['screen_name']
                except:
                    pass
                else:
                    all_followed_screen_name.append(screen_name)
            self.all_followed_screen_name = all_followed_screen_name
        # all_followed.reverse()
        # random.shuffle(all_followed)
        for index, follow in enumerate(all_followed):
            try:
                followed_screen_name = follow['content']['itemContent']['user']['legacy']['screen_name']
                followed_user_name = self.get_user_name(followed_screen_name)
                followed_user_id = follow['content']['itemContent']['user']['rest_id']
                tweets = self.get_tweets(followed_user_id)
            except Exception:
                print("all_followed fail:%s\ntraceback:%s" % (follow, traceback.format_exc()))
                time.sleep(30)
            else:
                if tweets is None:
                    print('tweets is None:%s' % followed_user_name)
                    continue
                else:
                    print('{}:get tweets success:{}'.format(followed_screen_name, len(tweets)))
                if depth == 0:
                    self.download_followed_depth(followed_screen_name, depth + 1)
                if depth == 1 and followed_screen_name not in self.all_followed_screen_name and len(tweets) > 10:
                    self.download_all_twitter(tweets, followed_screen_name, followed_user_name)

                # time.sleep(60)

                # self.rename_dir(followed_screen_name, legal_followed_user_name)
            finally:
                if depth == 0:
                    print('finish:%s' % (index))


if __name__ == '__main__':
    td = TwitterDownload()
    td.download_oneuser("NBA")
