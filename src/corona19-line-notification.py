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
        self.released = 0
        self.dead = 0
        self.extras: Dict[str, int] = {}

    # ex) 감염=5,격리해제=3,사망=2,추가정보={'신천지관련': 2},출처=occidere news
    def __str__(self):
        return '감염=%d,격리해제=%d,사망=%d%s출처=%s' % (
            self.infected, self.released, self.dead, ',추가정보={},'.format(self.extras) if self.extras else '', self.source
        )


def get_bs(url: str, encoding: str = 'utf-8') -> BeautifulSoup:
    req = get(url=url)
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
            if '확진자' == title:
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


# 보건복지부
def parse_mohw() -> [Corona19Status, None]:
    bs = get_bs(url='http://ncov.mohw.go.kr/index_main.jsp')
    corona19 = Corona19Status(source='보건복지부')

    try:
        co_cur = bs.find(name='div', attrs={'class': 'co_cur'})
        for li in co_cur.find_all(name='li'):
            title = li.find(name='span', attrs={'class': 'tit'}).text.strip()
            count = int(re.sub(pattern='[^0-9]', repl='', string=li.find(name='a', attrs={'class', 'num'}).text))
            if '확진환자수' == title:
                corona19.infected = count
            elif '확진환자 격리해제수' == title:
                corona19.released = count
            elif '사망자수' == title:
                corona19.dead = count
            else:
                corona19.extras[title] = count
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


def build_message(status: Corona19Status) -> str:
    msg = '''[코로나-19 현황]
- 확진자: {} 명
- 격리해제: {} 명
- 사망: {} 명
'''.format(status.infected, status.released, status.dead)

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
    merged_status = merge([parse_naver(), parse_mohw(), parse_sbs()])
    print('[{}] {}'.format(datetime.now(), merged_status))

    message = build_message(merged_status)
    print('[{}] {}'.format(datetime.now(), message))

    send_result = send_line_broadcast_message(message)
    print('[{}] {}'.format(datetime.now(), send_result))
