from argparse import ArgumentParser
import os
import pickle
import re
from datetime import datetime
from typing import *

from bs4 import BeautifulSoup
from linebot import LineBotApi
from linebot.exceptions import LineBotApiError
from linebot.models import TextSendMessage
from requests import *


class Corona19Status:
    def __init__(self, source: str):
        self.source: str = source
        self.infected = 0
        self.infected_delta = 0
        self.released = 0
        self.released_delta = 0
        self.dead = 0
        self.dead_delta = 0
        self.extras: Dict[str, int] = {}

    def set_count_by_title(self, title: str, count: int) -> None:
        if title in ['확진자', '확진환자']:
            self.infected = count
        elif title in ['격리해제', '완치자']:
            self.released = count
        elif title in ['사망자']:
            self.dead = count
        else:
            self.extras[title] = count

    # ex) 감염=5(+1),격리해제=3(+1),사망=2(-0),추가정보={'신천지관련': 2},출처=occidere news
    def __str__(self):
        return '감염=%d({}%d),완치자=%d({}%d),사망=%d({}%d)%s출처=%s'.format(
            '+' if self.infected_delta > 0 else '-',
            '+' if self.released_delta > 0 else '-',
            '+' if self.dead_delta > 0 else '-'
        ) % (
                   self.infected,
                   abs(self.infected_delta),
                   self.released,
                   abs(self.released_delta),
                   self.dead,
                   abs(self.dead_delta),
                   ',추가정보={},'.format(self.extras) if self.extras else '', self.source
               )


class Corona19DB:
    def __init__(self, db_path: str = 'corona19status.db'):
        self.db_path = db_path

    def read(self) -> [Corona19Status, None]:
        try:
            db_corona19 = Corona19Status(source='db')
            if os.path.exists(self.db_path):
                with open(file=self.db_path, mode='rb') as f:
                    db_corona19: Corona19Status = pickle.load(f)
                    db_corona19.source = 'db'
                    db_corona19.infected = db_corona19.infected
                    db_corona19.released = db_corona19.released
                    db_corona19.dead = db_corona19.dead
            return db_corona19
        except Exception as e:
            print('[{}] {}'.format(datetime.now(), e))
            return None

    def save(self, corona19_status: Corona19Status) -> None:
        try:
            pickle.dump(corona19_status, open(self.db_path, 'wb'))
        except Exception as e:
            print('[{}] {}'.format(datetime.now(), e))


def get_bs(url: str, encoding: str = 'utf-8') -> BeautifulSoup:
    req = get(url=url, headers={'User-Agent': 'Mozilla/5.0'})
    req.encoding = encoding
    return BeautifulSoup(markup=req.text, features='html.parser')


# SBS 데이터저널리즘팀 마부작침
def parse_sbs() -> [Corona19Status, None]:
    bs = get_bs(url='http://mabu.newscloud.sbs.co.kr/202002corona2/')
    corona19 = Corona19Status(source='SBS 데이터저널리즘팀 마부작침')

    try:
        for cb in bs.find_all(name='div', attrs={'class', 'currentbox'}):
            title, count = list(filter(None, cb.getText().strip().replace(' ', '').split('\n')))
            count = int(re.sub(pattern='[^0-9]', repl='', string=count))
            corona19.set_count_by_title(title, count)
    except Exception as e:
        print('[{}] {}'.format(datetime.now(), e))
        return None

    return corona19


# 보건복지부
def parse_mohw() -> [Corona19Status, None]:
    bs = get_bs(url='http://ncov.mohw.go.kr/')
    corona19 = Corona19Status(source='보건복지부 코로나바이러스감염증-19 현황')

    try:
        live_num_outer = bs.find(name='div', attrs={'class': 'liveNumOuter'})

        # 일일확진자, 일일완치자
        for li in live_num_outer.find(name='div', attrs={'class': 'liveNum_today_new'}).find_all(name='li'):
            title = li.select('span[class*=subtit]')[0].text.strip()
            count = int(re.sub(pattern='[^0-9]', repl='', string=li.select('span[class*=data]')[0].text))
            corona19.extras[title] = count

        # 확진환자, 완치, 치료중, 사망
        for li in live_num_outer.find(name='ul', attrs={'class': 'liveNum'}).find_all(name='li'):
            title = li.find(name='strong', attrs={'class': 'tit'}).text.strip()
            count = int(re.sub(pattern='[^0-9]', repl='', string=li.find(name='span', attrs={'class', 'num'}).text))
            corona19.set_count_by_title(title, count)
    except Exception as e:
        print('[{}] {}'.format(datetime.now(), e))
        return None

    return corona19


# NAVER
def parse_naver() -> [Corona19Status, None]:
    bs = get_bs(url='https://search.naver.com/search.naver?query=코로나바이러스감염증-19')
    corona19 = Corona19Status(source='NAVER')

    try:
        graph_view = bs.find(name='div', attrs={'class': 'graph_view'})
        for txt in graph_view.find_all(name='p', attrs={'class': 'txt'}):
            title = txt.find(name='span', attrs={'class': 'txt_sort'}).text.strip()
            count = int(re.sub(pattern='[^0-9]', repl='', string=txt.find(name='strong', attrs={'class': 'num'}).text))
            if '확진환자' == title:
                corona19.infected = count
            elif '격리해제' == title:
                corona19.released = count
            elif '사망자' == title:
                corona19.dead = count
            else:
                corona19.extras[title] = count
    except Exception as e:
        print('[{}] {}'.format(datetime.now(), e))
        return None

    return corona19


def merge(status_list: List[Corona19Status]) -> Corona19Status:
    """
    각 매체로부터 수집한 코로나-19 현황을 통합한다.
    확진자, 격리해제, 사망자에 해당하는 수치는 가장 높은 값을 사용하며 매체 정보는 , 로 이어붙인다.
    위에 해당되지 않는 자료는 추가 작업 없이 단순하게 합친다.
    :param status_list: 각 매체로 부터 수집한 코로나-19 정보
    :return: 규칙에 따라 병합된 코로나-19 객체
    """
    status_list = [status for status in status_list if status]

    merged = Corona19Status(source=','.join([status.source for status in status_list]))
    merged.infected = max([status.infected for status in status_list])
    merged.released = max([status.released for status in status_list])
    merged.dead = max([status.dead for status in status_list])

    for ext in [status.extras for status in status_list]:
        for k, v in ext.items():
            merged.extras[k] = v

    return merged


def apply_diff(corona19: Corona19Status, db_corona19: Corona19Status) -> bool:
    changed = False

    if corona19.infected != db_corona19.infected:
        changed = True
        corona19.infected_delta = corona19.infected - db_corona19.infected
    if corona19.released != db_corona19.released:
        changed = True
        corona19.released_delta = corona19.released - db_corona19.released
    if corona19.dead != db_corona19.dead:
        changed = True
        corona19.dead_delta = corona19.dead - db_corona19.dead

    # TODO extras 비교 필요

    return changed


def build_message(status: Corona19Status) -> str:
    msg = '''[코로나-19 현황]
- 확진자: {} 명 ({}{})
- 격리해제: {} 명 ({}{})
- 사망: {} 명 ({}{})
'''.format(
        status.infected,
        '+' if status.infected_delta > 0 else '-',
        abs(status.infected_delta),
        status.released,
        '+' if status.released_delta > 0 else '-',
        abs(status.released_delta),
        status.dead,
        '+' if status.dead_delta > 0 else '-',
        abs(status.dead_delta)
    )

    for k, v in status.extras.items():
        msg += '- {}: {} 명\n'.format(k, v)
    msg += '\n[데이터 출처]\n{}'.format('\n'.join(map(lambda src: '- ' + src, status.source.split(','))))

    return msg


def send_line_broadcast_message(msg: str) -> bool:
    line_bot_api = LineBotApi(channel_access_token='알람을_전송할_line_봇_토큰')
    try:
        line_bot_api.broadcast(messages=TextSendMessage(text=msg))
        print('[{}] line broadcast message sent successfully'.format(datetime.now()))
        return True
    except LineBotApiError as e:
        print('[{}] {}'.format(datetime.now(), e))
        return False


if __name__ == '__main__':
    parser = ArgumentParser('Messenger notification control.')
    parser.add_argument('--force-alert', dest='force_alert', action='store_true', help='이 옵션을 추가하면 강제로 알람을 전송함')
    parser.add_argument('--db-path', dest='db_path', default='corona19status.db', help='코로나 감염 현황을 관리할 file db 를 지정함')
    args = parser.parse_args()

    force_alert = args.force_alert
    db_path = args.db_path

    print('[{}] Force alert: {}'.format(datetime.now(), force_alert))
    print('[{}] db path: {}'.format(datetime.now(), db_path))

    merged_status = merge([parse_naver(), parse_mohw(), parse_sbs()])
    print('[{}] MERGED: {}'.format(datetime.now(), merged_status))

    db = Corona19DB(db_path=db_path)
    db_status = db.read()
    print('[{}] DB: {}'.format(datetime.now(), db_status))

    changed_status = apply_diff(corona19=merged_status, db_corona19=db_status)

    db.save(corona19_status=merged_status)
    print('[{}] DB 저장 완료 => {}'.format(datetime.now(), merged_status))

    if changed_status or force_alert:
        message = build_message(merged_status)
        print('[{}] {}'.format(datetime.now(), message))

        send_result = send_line_broadcast_message(message)
        print('[{}] {}'.format(datetime.now(), send_result))
    else:
        print('[{}] 변경사항이 없으므로 알림 skip'.format(datetime.now()))
