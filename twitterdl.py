import requests
import os
import re
from lxml import etree
import traceback
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from concurrent.futures import as_completed

from header_config import headers

proxies = {
    'http': 'http://127.0.0.1:1080',
    'https': 'https://127.0.0.1:1080',
}


class Twitter():
    base_url = 'https://api.twitter.com/2/timeline/media/{}.json?include_profile_interstitial_type=1&include_blocking=1&include_blocked_by=1&include_followed_by=1&include_want_retweets=1&include_mute_edge=1&include_can_dm=1&include_can_media_tag=1&skip_status=1&cards_platform=Web-12&include_cards=1&include_composer_source=true&include_ext_alt_text=true&include_reply_count=1&tweet_mode=extended&include_entities=true&include_user_entities=true&include_ext_media_color=true&include_ext_media_availability=true&send_error_codes=true&simple_quoted_tweets=true&count=10000&ext=mediaStats%2ChighlightedLabel%2CcameraMoment'
    member_list_url = 'https://api.twitter.com/1.1/lists/members.json?include_profile_interstitial_type=1&include_blocking=1&include_blocked_by=1&include_followed_by=1&include_want_retweets=1&include_mute_edge=1&include_can_dm=1&include_can_media_tag=1&skip_status=1&cards_platform=Web-12&include_cards=1&include_composer_source=true&include_ext_alt_text=true&include_reply_count=1&tweet_mode=extended&count=1000&list_id={}'
    member_list_id_api = 'https://api.twitter.com/1.1/lists/ownerships.json?include_profile_interstitial_type=1&include_blocking=1&include_blocked_by=1&include_followed_by=1&include_want_retweets=1&include_mute_edge=1&include_can_dm=1&include_can_media_tag=1&skip_status=1&cards_platform=Web-12&include_cards=1&include_composer_source=true&include_ext_alt_text=true&include_reply_count=1&tweet_mode=extended&cursor=-1&user_id={}'
    member_path = r'K:\爬虫\twitter\newmemberlist'
    headers = headers

    def __init__(self, user_name=None):
        self.user_name = user_name

    def get_tweets(self, user_id):
        for i in range(1, 5):
            try:
                url = self.base_url.format(user_id)
                res = requests.get(url=url, proxies=proxies, headers=self.headers, timeout=i * 30).json()
                tweets = res.get('globalObjects').get('tweets')
            except Exception:
                print('get_tweets fail')
                print(traceback.format_exc())
            else:
                print('get_tweets success:%s' % len(tweets))
                return tweets

    def get_user_id(self, user_name):
        for i in range(5):
            try:
                page_source = requests.get('https://twitter.com/{user_name}'.format(user_name=user_name),
                                           proxies=proxies, timeout=(i + 1) * 30).text
                selector = etree.HTML(page_source)
                user_id = str(selector.xpath('//div[@class="ProfileNav"]/@data-user-id')[0])
            except:
                print('%d time get_user_id fail' % (i + 1))
            else:
                print('get_user_id success:%s' % user_id)
                return user_id

    def save_file(self, download_url, save_dir, legal_file_name):
        file_path = os.path.join(save_dir, legal_file_name)
        if os.path.exists(file_path):
            print('已经下载:%s' % file_path)
            return
        for i in range(5):
            try:
                content = requests.get(download_url, timeout=(i + 1) * 60, proxies=proxies).content
                file_path = os.path.join(save_dir, legal_file_name)
                with open(file_path, 'wb') as f:
                    f.write(content)
            except Exception as e:
                print(traceback.format_exc())
            else:
                print(file_path)
                return

    def get_max_video_url(self, media):
        variants = media['video_info']['variants']
        variants_video = [variant for variant in variants if variant.get('bitrate')]
        sort_variants_video = sorted(variants_video, key=lambda x: x.get('bitrate'))
        max_video_url = sort_variants_video[-1]['url']
        return max_video_url

    def dowload_one_twitter(self, tweet, save_dir):
        try:
            full_text = tweet['full_text']
            id_str = tweet['id_str']
            fix_text = full_text.split('http')[0]
            legal_file_name = re.sub(r"[^\w]", "", fix_text)
            if not legal_file_name:
                legal_file_name = id_str
            media_list = tweet['extended_entities']['media']
            for index, media in enumerate(media_list):
                type = media['type']
                if type == 'video':
                    download_url = self.get_max_video_url(media)
                    # download_url = sorted(media['video_info']['variants'],key=lambda x:x.get('bitrate)',reverse=True)['url'])
                    legal_save_name = legal_file_name
                    file_size = download_url.split('vid/')[-1].split('/')[0]
                    legal_save_name = legal_save_name + '_' + file_size
                else:
                    download_url = media['media_url']
                    if index != 0:
                        legal_save_name = legal_file_name + '_' + str(index)
                    else:
                        legal_save_name = legal_file_name
                file_format = download_url.split("?")[0].split('.')[-1]
                legal_save_name = legal_save_name + '.' + file_format
                self.save_file(download_url, save_dir, legal_save_name)
        except Exception as e:
            print(traceback.format_exc())

    def download(self, tweets, user_name):
        save_dir = os.path.join(self.member_path, user_name)
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)
            print('makedirs:%s' % save_dir)
        # with ThreadPoolExecutor(max_workers=10) as executor:
        with ThreadPoolExecutor() as executor:
            t_dict = {executor.submit(self.dowload_one_twitter, tweet, save_dir): tweet for tweet in tweets.values()}
            for future in as_completed(t_dict):
                tweet = t_dict[future]
                try:
                    future.result()
                except Exception:
                    print('download异常:%s' % tweet + '\n', traceback.format_exc())

        # for tweet in tweets.values():
        #     self.dowload_one_twitter(tweet, save_dir)

    def get_member_list(self, user_name):
        user_id = self.get_user_id(user_name)
        try:
            member_list_id = \
            requests.get(url=self.member_list_id_api.format(user_id), proxies=proxies, headers=self.headers).json()[
                'lists'][0]['id_str']
            res = requests.get(url=self.member_list_url.format(member_list_id), proxies=proxies,
                               headers=self.headers).json()
            members = res['users']
        except Exception as e:
            print(traceback.format_exc())
        else:
            return members

    def get_user_name(self, screen_name):
        try:
            url = 'https://api.twitter.com/graphql/P8ph10GzBbdMqWZxulqCfA/UserByScreenName?variables=%7B%22screen_name%22%3A%22{}%22%2C%22withHighlightedLabel%22%3Atrue%7D'.format(
                screen_name)
            res = requests.get(url, proxies=proxies, timeout=30, headers=self.headers).json()
            username = res['data']['user']['legacy']['name']
        except Exception as e:
            print(traceback.format_exc())
            username = screen_name

        # legal_user_name = re.sub(r"[\/\\\:\*\?\"\<\>\|!！\.\s]", "", username)
        legal_user_name = re.sub(r"[^\w]", "", username)
        if not legal_user_name:
            legal_user_name = screen_name
        return legal_user_name

    def download_oneuser(self, screen_name):
        print('start download_oneuser:%s' % screen_name)
        user_id = self.get_user_id(screen_name)
        user_name = self.get_user_name(screen_name)
        tweets = self.get_tweets(user_id)
        self.download(tweets, user_name)

    def download_member_list(self, username):
        members = self.get_member_list(username)
        for member in members:
            screen_name = member.get('screen_name')
            user_name = member.get('name')
            self.download_oneuser(screen_name)


if __name__ == '__main__':
    t = Twitter()
    # t.download_oneuser('NBA')
    t.download_member_list("NBA")
