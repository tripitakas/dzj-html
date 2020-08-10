#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
import sys
from os import path
from tornado.options import options
from elasticsearch import Elasticsearch

BASE_DIR = path.dirname(path.dirname(path.dirname(path.dirname(__file__))))
sys.path.append(BASE_DIR)

from controller.helper import load_config
from controller.page.tool.diff import Diff
from controller.page.tool.variant import normalize


def get_hosts():
    config = load_config() or {}
    hosts = [config.get('esearch')]
    if hasattr(options, 'testing') and options.testing:
        hosts = [dict(host='dev.tripitakas.net')]
    return hosts


def find(q, index='cb4ocr-ik'):
    """ 从ES中寻找与q最匹配的document """
    if not q:
        return []

    if re.match(r'^[0-9a-zA-Z_]+', q):
        match = {'page_code': q}
    else:
        ocr = re.sub(r'[\x00-\xff]', '', q)
        ocr = re.sub(Diff.cmp_junk_char, '', ocr)
        match = {'normal': normalize(ocr)}

    dsl = {
        'query': {'match': match},
        'highlight': {'pre_tags': ['<kw>'], 'post_tags': ['</kw>'], 'fields': {'normal': {}}}
    }

    es = Elasticsearch(hosts=get_hosts())
    r = es.search(index=index, body=dsl)

    return r['hits']['hits']


def find_one(ocr, num=1):
    """ 从ES中寻找与ocr最匹配的document，返回第num个结果 """
    ocr = ''.join(ocr) if isinstance(ocr, list) else ocr.replace('|', '')
    ret = find(ocr)
    if not ret or num - 1 not in range(0, len(ret)):
        return '', []
    hit_page_codes = [r['_source']['page_code'] for r in ret]
    cb = ''.join(ret[num - 1]['_source']['origin'])
    diff = Diff.diff(ocr, cb, label=dict(base='ocr', cmp1='cb'))[0]
    txt = ''.join(['<kw>%s</kw>' % d['cb'] if d.get('is_same') else d['cb'] for d in diff])
    return txt.strip('\n'), hit_page_codes


def find_neighbor(page_code, neighbor='next'):
    """ 从ES中寻找page_code的前一页或后一页记录 """
    assert neighbor in ['prev', 'next']
    head = re.search(r'^([A-Z]{1,2}\d+n[A-Z]?\d+[A-Za-z_]?)p([a-z]?\d+)', page_code)
    page_no = head.group(2)
    neighbor_no = str(int(page_no) + 1 if neighbor == 'next' else int(page_no) - 1).zfill(len(page_no))
    neighbor_code = '%sp%s' % (head.group(1), neighbor_no)
    neighbor_node = find(neighbor_code)
    return neighbor_node and neighbor_node[0]


def find_match(ocr):
    """ 从cbeta文中找出与ocr匹配的文本"""
    ocr = ''.join(ocr) if isinstance(ocr, list) else ocr.replace('|', '')
    if len(ocr) < 10 or (len(ocr) < 20 and re.findall(r'[第苐][一二三四五六七八九十]+[張张]', ocr)):
        return ''
    ret = find(ocr)
    if not ret:
        return ''
    cb = ''.join(ret[0]['_source']['origin'])
    diff = Diff.diff(ocr, cb, label=dict(base='ocr', cmp1='cb'))[0]
    # 寻找第一个和最后一个同文
    start, end = 0, 0
    for i, d in enumerate(diff):
        if d.get('is_same') and len(d['ocr']) > 2 and not start:
            start = i
        if diff[-i - 1].get('is_same') and len(d['ocr']) > 2 and not end:
            end = len(diff) - i - 1
        if start and end:
            break
    match = ''
    if start > 0:
        _ocr = ''.join([d['ocr'] for d in diff[:start]])
        match1 = find_match(_ocr)
        match += match1
    if end >= start:
        match2 = ''.join([d['cb'] for d in diff[start:end + 1]])
        match += match2
    if end + 1 < len(diff):
        _ocr = ''.join([d['ocr'] for d in diff[end + 1:]])
        match3 = find_match(_ocr)
        match += match3
    return match


if __name__ == '__main__':
    ocr_txt = '杉卜卜巾巾十七专苐三十六張坐只只|衆魔邪業普現卜切世界行菩薩行|以善方便廣爲衆生說諸佛法捨離|愚癡隨順一切佛法智慧菩薩摩訶|薩隨所生處行住坐臥一切常得不|壞眷屬得淸淨念悉能聞持三世一|切諸如來法盡未來際劫行菩薩行|未曾休息而無染著得普賢行諸願|滿足得一切智施作佛事悉得諸佛|菩薩無量自在爾時金州幢菩薩承|佛神力普觀十方以偈頌日|菩薩未曾有慢心一切諸方無比尊|隨本所修功德業亦復不起輕慢心|所修一切諸功德不潙自已及他人|以無縛著解脫心迴向饒益一切衆|永囄一切自高顯亦復棄捨憍慢心|於最勝所起身業勸誚說法種種行|所作無量諸功德饒益一切衆生類|安住無著解脫心迴向一切諸如來|世閒無量群生類種種方便諸伎術|勝妙甚深微細事悉能具足分別知|世閒所有種種身斯由身業之所得|覺悟無量生死行逮得不退智慧門|十方卜切无量剎微細勝妙伏世界||古華蠻絲苐十七庵苐三十七張坐字亥|菩薩深入智慧門於一毛孔悉了矢|一切衆生無量心明者了知卽一心|菩薩覺悟智慧門不捨增長諸業行|一切衆生種種根上中下品各不同|所有甚深諸功德菩薩隨性悉了知|一切衆生種種業上中下品差別相|菩薩深入如來力悉能具足分別知|不可思議無量劫悉能了知卽惹念|一均十方所行業菩薩覺悟淸淨知|悉能逆順知三世分別其相各不同|而亦不違平等杻是則囄癡菩薩行|卜切衆生無量行愛慢諸結各不同|菩薩別相分別知亦復不捨無相觀|十方世界諸如來具足示現大自在|難見難得難思議菩薩悉能分別知|兜率陁天大導師无比最勝人師子|功德甚深廣淸淨一切如實見其性|示現降神處母胎無量自在大神變|成佛涅槃轉法輪一切世閒莫能轉|人中師子初生時一切諸勝悉奉敬|天王帝釋梵天王諸有智者悉敬侍|十方一切无有餘無量无數諸法界|无始無末无中閒示現无量自在力||古幸弟澣礱十乀卞菟三十八扑坐字于|人中尊導現生已遊行諸方各七步|觀察一切衆生類無㝵法門覺一切|觀見衆生沒五欲人中師子現微笑|衆生盲冥愚癡覆我當度脫三有苦|大師子吼出妙音我爲世閒第一尊|顯現明淨智慧燈永滅生死愚癡闇|人中師子出世閒放大光明無有量|斷除一切諸惡道无量衆苦究竟滅|或時示現處宮殿或現捨家行學道|人中師子現自在饒益一切衆生故|菩薩初坐道場時六反震動諸大地|普放無量大光明遍照五道衆生類|震動一切魔宮殿開發十方衆生心|昔於菩薩有緣者皆悉覺悟眞實義|一毛道中無量乘十方一切諸佛剎|衆生道乘無有量彼現最勝大神變|如是方便隨順覺如一切佛所演說|若諸如來所不說亦悉解了分別知|除滅一切衆魔怨普覆三千大千界|深入一切无㝵門能壞一切諸魔道|如來或在諸佛剎或復現處諸天宮|或復現身梵宮殿菩薩悉見无障㝵|轉於淸淨妙法輪如采法身无邊際'
    res = find_match(ocr_txt)
    print(res)
