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
        if diff[-i - 1].get('is_same') and len(diff[-i - 1]['ocr']) > 2 and not end:
            end = len(diff) - i - 1
        if start and end:
            break
    match = ''
    if start > 0:
        _ocr = ''.join([d['ocr'] for d in diff[:start]])
        match1 = find_match(_ocr)
        match += match1
    if start and end >= start:
        match2 = ''.join([d['cb'] for d in diff[start:end + 1]])
        match += match2
    if end and end + 1 < len(diff):
        _ocr = ''.join([d['ocr'] for d in diff[end + 1:]])
        match3 = find_match(_ocr)
        match += match3
    return match


if __name__ == '__main__':
    ocr_txt = '壬甘柩沜采二加弟丨允蒲汁字兮|十種一切解脫光明雲悉皆彌覆充|滿虛空來詣佛所供養恭敬札拜巳|在於上方妙音勝蓮華藏師寸座上|結加趺坐如是等十億佛剎塵數世|界海中有十億佛剎微麈數等大菩|薩來一一菩薩各將一佛世界麈數|菩薩以爲眷屬一一菩薩各與一佛|世界微塵數等妙莊嚴雲悉皆彌覆|充滿虛空隨所來方結加趺坐彼諸|菩薩次第坐已一切毛孔各出十佛|世界微塵數等一切妙寶淨光明雲|一一光中各出十佛世界塵數菩薩|一二菩薩剿切法界方便海充滿一|切微塵道一一塵中有十佛世界塵|數佛剎一一佛剎中三世諸沸皆悉|顯現念念中於一卜世界各化一佛|剎塵數衆生以夢自在示現法門教|化一切諸天化生法門教化一切菩|薩行處音聲法門教化震動莆切佛|剎建立諸佛法門教化一切願海法|門教化一切衆生言辞入佛音聲法|門教化一切佛法雲雨法門教化法|界白在光明法門教化建立二切大||十選甫卜鸞壬毛專于斗引漫嵒兮|衆海於普賢苦薩法門教化以如是|等一切法門隨其所樂而教化之於|一念頃能滅一切世界中各如湏彌|山麈數衆生諸惡道苦各如湏彌山|塵數衆生令囄邪定立正定聚各如|湏彌山塵數衆生令立聲聞緣覺之|地各如湏彌山塵數衆生立无上道|各如湏彌山塵數衆生立一切不可|畫功德智慧地各如湏彌山塵數衆|生令立盧舍那佛願性海中爾時諸|菩薩光明中以偈頌曰|一切光明出妙音說諸菩薩具足行|佛子功德悉成蒲普遍一切十方界|无量劫海修行道欲令衆生離苦故|不自計巳生死苦佛子善入大方便|无量无邊無有餘窮盡一切大海劫|遍行一切諸法門善說微妙寂靜法|一切三世佛肝願皆得淸淨具足滿|佛子饒益諸衆生能自具行淸淨道|皆能往詣諸佛所淸淨法身照十方|佛于智海无邊底普觀諸法寂減相|四光明中有无量无上大慈難思議|渚淨慧眼照諸法此是佛子妙境界||亅丷氵郞苐十只只只巾兮|一七悉受諸佛剎又能震動諸國土|能令衆生无怖想是名淸淨方便地|一一塵中无量身復現无量莊嚴剎|於一念中皆悉見是无障㝵淨法門|三世所有一切卻於一念中能悉現|猶如幻化無肝有是名渚佛无㝵法|普賢諸行皆具足能令衆生悉淸淨|諸佛子具自在法一一毛孔師子吼|爾時世尊欲令一切菩薩大衆知佛|无量無邊境界白在法門故放眉閒|白毫相凶切寶色燈明雲光名一切|菩薩慧光觀察照十方藏此光遍照|一切佛剎於一念中皆悉普照一切|法界於一切世界雨一切佛諸大願|雲顯現普賢菩薩示大衆巳還從足|下相輪中入於彼復有大蓮華生以|衆寶爲莖一切寶王爲莊嚴藏其葉|遍覆一切法界一切寶香莊嚴其鬚|閻浮檀金以爲其臺此華生巳如來|眉間有一大菩薩出名日一切諸法|勝音輿世界海塵數菩薩衆俱敬繞|世尊无量帀巳退坐蓮華臺上眷暴|菩薩坐蓮嘗鬚一仞渚法勝音菩薩'
    res = find_match(ocr_txt)
    print(res)
