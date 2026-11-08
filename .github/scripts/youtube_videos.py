# 신차마켓 유튜브 최신 쇼츠 목록(videos.json) 갱신 스크립트
# GitHub Actions(.github/workflows/youtube.yml)가 주기적으로 실행합니다.
# 유튜브 RSS가 가끔 404를 내므로, 실패하면 다른 경로로 차례대로 시도합니다.
import json
import re
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

CHANNEL = 'UClc5O2WE0EOxGIWgbrxCmXg'
LIMIT = 8
OUT = 'videos.json'
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                  '(KHTML, like Gecko) Chrome/124.0 Safari/537.36',
    'Accept-Language': 'ko-KR,ko;q=0.9',
}
NS = {'a': 'http://www.w3.org/2005/Atom', 'yt': 'http://www.youtube.com/xml/schemas/2015'}


def get(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def from_feed(url, shorts_only_links):
    root = ET.fromstring(get(url))
    out = []
    for e in root.findall('a:entry', NS):
        vid = e.findtext('yt:videoId', default='', namespaces=NS)
        link = e.find('a:link', NS)
        href = link.get('href', '') if link is not None else ''
        if not vid or (shorts_only_links and '/shorts/' not in href):
            continue
        out.append({'id': vid, 'title': e.findtext('a:title', default='', namespaces=NS)})
    return out


def shorts_playlist_feed():
    # UUSH = 이 채널의 쇼츠만 모인 자동 재생목록
    return from_feed('https://www.youtube.com/feeds/videos.xml?playlist_id=UUSH' + CHANNEL[2:], False)


def channel_feed():
    return from_feed('https://www.youtube.com/feeds/videos.xml?channel_id=' + CHANNEL, True)


def shorts_page():
    html = get('https://www.youtube.com/channel/' + CHANNEL + '/shorts').decode('utf-8', 'replace')
    ids = []
    for m in re.finditer(r'/shorts/([\w-]{11})', html):
        if m.group(1) not in ids:
            ids.append(m.group(1))
    out = []
    for vid in ids[:LIMIT]:
        title = ''
        try:
            q = urllib.parse.quote('https://www.youtube.com/shorts/' + vid, safe='')
            title = json.loads(get('https://www.youtube.com/oembed?format=json&url=' + q)).get('title', '')
        except Exception as e:
            print('  제목 못 가져옴', vid, e)
        out.append({'id': vid, 'title': title})
    return out


SOURCES = [
    ('쇼츠 재생목록 RSS', shorts_playlist_feed),
    ('채널 RSS', channel_feed),
    ('채널 쇼츠 페이지', shorts_page),
]


def main():
    for name, fn in SOURCES:
        for attempt in range(1, 4):
            try:
                videos = fn()
            except Exception as e:
                print(f'{name} 실패 ({attempt}/3): {e}')
                time.sleep(5 * attempt)
                continue
            if not videos:
                print(f'{name}: 영상 없음')
                break
            with open(OUT, 'w', encoding='utf-8') as f:
                json.dump({'videos': videos[:LIMIT]}, f, ensure_ascii=False, indent=1)
                f.write('\n')
            print(f'{name}에서 쇼츠 {len(videos[:LIMIT])}개 저장')
            return
    print('모든 경로 실패 - 기존 videos.json을 그대로 둡니다')


if __name__ == '__main__':
    main()
    sys.exit(0)
