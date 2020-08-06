#!/usr/bin/env python
# -*- coding: utf-8 -*-
# python3 utils/update_exam_data.py --uri=uri --func=initial_run
# 更新考核和体验相关的数据和任务

import sys
import random
import pymongo
from os import path

BASE_DIR = path.dirname(path.dirname(__file__))
sys.path.append(BASE_DIR)

from controller import helper as hp
from controller.base import BaseHandler as Bh
from controller.page.base import PageHandler as Ph

names1 = ['GL_1054_1_4', 'GL_78_9_18', 'JX_260_1_98', 'JX_260_1_239', 'YB_33_629', 'QL_26_175', 'YB_26_512',
          'YB_27_906', 'QL_24_691', 'QL_10_446']
names2 = ['GL_9_1_12', 'GL_1260_9_5', 'JX_260_1_103', 'JX_260_1_270', 'YB_25_931', 'QL_2_354', 'YB_32_967', 'YB_22_995',
          'QL_13_413', 'QL_4_629']
names3 = ['GL_1260_1_3', 'GL_922_2_21', 'JX_260_1_135', 'JX_260_1_194', 'YB_28_965', 'QL_10_413', 'YB_28_423',
          'YB_27_377', 'QL_24_17', 'QL_11_145']
names4 = ['GL_82_1_5', 'GL_1056_1_20', 'JX_260_1_280', 'JX_260_1_181', 'YB_28_867', 'QL_14_17', 'YB_28_171',
          'YB_29_769', 'QL_25_416', 'QL_1_210']
names5 = ['GL_1056_2_21', 'GL_62_1_37', 'JX_260_1_148', 'JX_245_3_100', 'YB_29_813', 'QL_10_715', 'YB_26_41',
          'YB_30_159', 'QL_25_48', 'QL_10_571']
names6 = ['GL_165_1_28', 'GL_922_1_21', 'JX_260_1_83', 'JX_260_2_12', 'YB_28_797', 'QL_12_176', 'YB_26_172',
          'YB_23_132', 'QL_13_481', 'QL_7_385']
names7 = ['GL_923_2_16', 'GL_1054_4_2', 'JX_260_1_175', 'JX_260_1_91', 'YB_34_151', 'QL_7_337', 'YB_31_636',
          'YB_31_692', 'QL_1_309', 'QL_9_496']
names8 = ['GL_165_1_12', 'GL_914_1_20', 'JX_260_1_64', 'JX_260_1_210', 'YB_24_228', 'QL_10_160', 'YB_33_418',
          'YB_25_562', 'QL_25_400', 'QL_9_513']
names9 = ['GL_1051_7_23', 'GL_9_1_16', 'JX_260_2_23', 'JX_245_3_142', 'YB_24_667', 'QL_24_71', 'YB_33_748', 'YB_27_257',
          'QL_26_391', 'QL_2_772']
names10 = ['GL_1434_5_10', 'GL_129_1_11', 'JX_260_1_249', 'JX_260_1_17', 'YB_29_283', 'QL_11_112', 'YB_24_400',
           'YB_25_108', 'QL_7_401', 'QL_11_375']
names11 = ['GL_1047_1_11', 'YB_22_389', 'YB_22_346', 'QL_10_526', 'QL_10_145', 'JX_165_7_115', 'GL_1047_1_15',
           'YB_22_476', 'YB_22_713', 'QL_10_17']
names12 = ['GL_1047_1_21', 'YB_22_816', 'YB_22_555', 'QL_10_572', 'QL_10_192', 'JX_165_7_12', 'GL_1047_1_34',
           'YB_22_759', 'YB_23_25', 'QL_10_208']
names13 = ['GL_1047_1_5', 'YB_23_570', 'YB_22_916', 'QL_11_46', 'QL_10_224', 'JX_165_7_135', 'GL_1047_2_17',
           'YB_23_182', 'YB_23_711', 'QL_10_241']
names14 = ['GL_1047_3_15', 'YB_23_721', 'YB_23_423', 'QL_13_340', 'QL_10_287', 'JX_165_7_18', 'GL_1047_3_5',
           'YB_23_477', 'YB_23_839', 'QL_10_302']
names15 = ['GL_1047_4_35', 'YB_23_880', 'YB_23_542', 'QL_13_430', 'QL_10_318', 'JX_165_7_27', 'GL_1048_1_19',
           'YB_23_574', 'YB_23_882', 'QL_10_351']
names16 = ['GL_1048_1_22', 'YB_23_885', 'YB_23_639', 'QL_14_82', 'QL_10_397', 'JX_165_7_30', 'GL_1048_1_25',
           'YB_23_727', 'YB_23_899', 'QL_10_429']
names17 = ['GL_1048_1_39', 'YB_23_906', 'YB_23_890', 'QL_24_332', 'QL_10_462', 'JX_165_7_43', 'GL_1048_1_43',
           'YB_24_204', 'YB_23_911', 'QL_10_477']
names18 = ['GL_1048_2_21', 'YB_23_913', 'YB_24_47', 'QL_25_313', 'QL_10_493', 'JX_165_7_70', 'GL_1048_2_26',
           'YB_24_522', 'YB_23_923', 'QL_10_509']
names19 = ['GL_1048_2_29', 'YB_23_928', 'YB_24_813', 'QL_10_525', 'JX_165_7_72', 'GL_1048_2_30', 'YB_24_862',
           'YB_24_110', 'QL_10_542', 'JX_165_7_75']
names20 = ['GL_1048_2_59', 'YB_24_113', 'YB_24_910', 'QL_10_556', 'JX_165_7_85', 'GL_1049_1_10', 'YB_25_207',
           'YB_24_119', 'QL_10_588', 'JX_165_7_87']
names21 = ['GL_1049_1_15', 'YB_24_126', 'YB_25_23', 'QL_10_603', 'JX_245_1_130', 'GL_1049_1_21', 'YB_25_319',
           'YB_24_132', 'QL_10_619', 'JX_245_1_133']
names22 = ['GL_1049_1_27', 'YB_24_210', 'YB_25_377', 'QL_10_635', 'JX_245_1_136', 'GL_1049_1_4', 'YB_25_474',
           'YB_24_215', 'QL_10_651', 'JX_245_1_138']
names23 = ['GL_1049_1_53', 'YB_24_219', 'YB_25_520', 'QL_10_667', 'JX_245_1_140', 'GL_1051_7_17', 'YB_25_600',
           'YB_24_226', 'QL_10_683', 'JX_245_1_146']
names24 = ['GL_1051_7_25', 'YB_24_232', 'YB_25_692', 'QL_10_699', 'JX_245_1_153', 'GL_1051_8_11', 'YB_25_840',
           'YB_24_234', 'QL_11_16', 'JX_245_1_21']
names25 = ['GL_1051_8_9', 'YB_24_238', 'YB_25_897', 'QL_11_212', 'JX_245_1_24', 'GL_1054_1_11', 'YB_26_203', 'YB_24_24',
           'QL_11_275', 'JX_245_1_44']
names26 = ['GL_1054_1_12', 'YB_24_248', 'YB_26_263', 'QL_11_293', 'JX_245_1_49', 'GL_1054_1_13', 'YB_26_333',
           'YB_24_251', 'QL_11_310', 'JX_245_1_70']
names27 = ['GL_1054_1_14', 'YB_24_257', 'YB_26_463', 'QL_11_327', 'JX_245_2_128', 'GL_1054_1_19', 'YB_26_559',
           'YB_24_259', 'QL_11_358', 'JX_245_2_150']
names28 = ['GL_1054_1_23', 'YB_24_262', 'YB_26_607', 'QL_11_392', 'JX_245_2_151', 'GL_1054_1_3', 'YB_26_638',
           'YB_24_264', 'QL_11_409', 'JX_245_2_152']
names29 = ['GL_1054_2_11', 'YB_24_267', 'YB_26_745', 'QL_11_426', 'JX_245_2_154', 'GL_1054_2_15', 'YB_26_834',
           'YB_24_269', 'QL_11_443', 'JX_245_2_155']
names30 = ['GL_1054_3_2', 'YB_24_271', 'YB_26_959', 'QL_11_477', 'JX_245_2_156', 'GL_1054_3_20', 'YB_27_107',
           'YB_24_273', 'QL_11_510', 'JX_245_2_157']
names31 = ['GL_1054_4_4', 'YB_24_579', 'YB_27_191', 'QL_11_542', 'JX_245_2_158', 'GL_1054_4_5', 'YB_27_45', 'YB_24_663',
           'QL_11_623', 'JX_245_2_159']
names32 = ['GL_1054_4_7', 'YB_24_665', 'YB_27_480', 'QL_11_639', 'JX_245_2_160', 'GL_1054_5_13', 'YB_27_563',
           'YB_24_807', 'QL_11_655', 'JX_245_2_161']
names33 = ['GL_1054_5_4', 'YB_25_106', 'YB_27_673', 'QL_11_671', 'JX_245_2_162', 'GL_1054_5_5', 'YB_27_75', 'YB_25_334',
           'QL_11_688', 'JX_245_2_163']
names34 = ['GL_1054_6_2', 'YB_25_371', 'YB_27_772', 'QL_11_706', 'JX_245_2_164', 'GL_1056_1_16', 'YB_27_822',
           'YB_25_375', 'QL_11_96', 'JX_245_2_165']
names35 = ['GL_1056_1_22', 'YB_25_856', 'YB_27_978', 'QL_12_123', 'JX_245_2_167', 'GL_1056_1_27', 'YB_28_250',
           'YB_25_858', 'QL_12_141', 'JX_245_2_168']
names36 = ['GL_1056_1_28', 'YB_26_337', 'YB_28_295', 'QL_12_159', 'JX_245_2_173', 'GL_1056_1_8', 'YB_28_370',
           'YB_26_780', 'QL_12_193', 'JX_245_2_179']
names37 = ['GL_1056_2_10', 'YB_26_783', 'YB_28_492', 'QL_12_210', 'JX_245_2_189', 'GL_1056_2_17', 'YB_28_524',
           'YB_26_797', 'QL_12_227', 'JX_245_2_19']
names38 = ['GL_1056_2_18', 'YB_26_862', 'YB_28_557', 'QL_12_261', 'JX_245_2_23', 'GL_1056_2_20', 'YB_28_624',
           'YB_26_864', 'QL_12_35', 'JX_245_2_42']
names39 = ['GL_1056_2_22', 'YB_26_866', 'YB_28_918', 'QL_12_449', 'JX_245_3_174', 'GL_1056_2_24', 'YB_29_104',
           'YB_26_870', 'QL_12_465', 'JX_245_2_75']
names40 = ['GL_1056_2_26', 'YB_26_874', 'YB_29_245', 'QL_12_481', 'JX_245_3_175', 'GL_1056_2_3', 'YB_29_269',
           'YB_26_890', 'QL_12_497', 'JX_245_3_1']
names41 = ['GL_1056_2_4', 'YB_26_898', 'YB_29_30', 'QL_12_512', 'JX_245_3_102', 'GL_1056_2_6', 'YB_29_599', 'YB_26_929',
           'QL_12_528', 'JX_245_3_104']
names42 = ['GL_1056_3_11', 'YB_27_531', 'YB_29_677', 'QL_12_544', 'JX_245_3_111', 'GL_1056_3_2', 'YB_29_861',
           'YB_27_54', 'QL_12_561', 'JX_245_3_115']
names43 = ['GL_1056_3_29', 'YB_27_594', 'YB_29_953', 'QL_12_577', 'JX_245_3_120', 'GL_1056_3_37', 'YB_30_207',
           'YB_27_613', 'QL_12_611', 'JX_245_3_121']
names44 = ['GL_1056_4_11', 'YB_27_625', 'YB_30_362', 'QL_12_644', 'JX_245_3_126', 'GL_1056_4_15', 'YB_30_413',
           'YB_27_633', 'QL_12_660', 'JX_245_3_130']
names45 = ['GL_1056_4_16', 'YB_27_638', 'YB_30_454', 'QL_12_696', 'JX_245_3_141', 'GL_1056_4_7', 'YB_30_577',
           'YB_27_654', 'QL_12_72', 'JX_245_3_146']
names46 = ['GL_1056_5_10', 'YB_27_659', 'YB_30_623', 'QL_12_729', 'JX_245_3_148', 'GL_1056_5_12', 'YB_30_708',
           'YB_27_68', 'QL_12_746', 'JX_245_3_153']
names47 = ['GL_1056_5_13', 'YB_28_455', 'YB_30_774', 'QL_12_763', 'JX_245_3_159', 'GL_1056_5_15', 'YB_30_80',
           'YB_28_476', 'QL_13_108', 'JX_245_3_160']
names48 = ['GL_1056_5_6', 'YB_28_500', 'YB_30_894', 'QL_13_124', 'JX_245_3_161', 'GL_1260_10_10', 'YB_31_24',
           'YB_28_515', 'QL_13_141', 'JX_245_3_164']
names49 = ['GL_1260_10_6', 'YB_28_529', 'YB_31_297', 'QL_13_158', 'JX_245_3_168', 'GL_1260_10_7', 'YB_31_312',
           'YB_28_594', 'QL_13_174', 'JX_245_3_170']
names50 = ['GL_1260_10_8', 'YB_28_600', 'YB_31_354', 'QL_13_18', 'JX_245_3_171', 'GL_1260_10_9', 'YB_31_422',
           'YB_28_604', 'QL_13_190', 'JX_245_3_173']

txt_kinds1 = ['也', '一', '不', '十', '無', '察', '記', '畢', '檀', '壞']
txt_kinds2 = ['二', '佛', '是', '法', '如', '馱', '愚', '舌', '救', '于']
txt_kinds3 = ['薩', '三', '有', '諸', '大', '致', '聚', '苾', '更', '治']
txt_kinds4 = ['生', '若', '菩', '所', '爲', '徧', '毀', '賀', '尸', '盧']
txt_kinds5 = ['羅', '卷', '經', '得', '故', '梨', '東', '昔', '鬼', '默']
txt_kinds6 = ['於', '衆', '此', '者', '世', '鼻', '怛', '北', '志', '歎']
txt_kinds7 = ['之', '四', '行', '摩', '善', '觸', '迷', '頂', '含', '遍']
txt_kinds8 = ['說', '以', '多', '心', '人', '煩', '乏', '風', '執', '吉']
txt_kinds9 = ['等', '五', '名', '能', '界', '花', '造', '干', '末', '體']
txt_kinds10 = ['音', '中', '第', '波', '僧', '反', '類', '調', '唯', '究']
txt_kinds11 = ['云', '言', '而', '上', '六', '對', '旣', '樓', '火', '拏']
txt_kinds12 = ['時', '子', '亦', '淨', '道', '請', '猶', '輕', '寂', '密']
txt_kinds13 = ['智', '來', '天', '方', '婆', '禪', '計', '牟', '譬', '近']
txt_kinds14 = ['其', '受', '我', '七', '阿', '到', '胡', '沒', '雨', '跋']
txt_kinds15 = ['比', '作', '相', '知', '尼', '座', '順', '耳', '邏', '癡']
txt_kinds16 = ['應', '身', '可', '八', '種', '芻', '墮', '部', '惟', '閒']
txt_kinds17 = ['自', '蜜', '訶', '何', '見', '破', '終', '曇', '隸', '晉']
txt_kinds18 = ['現', '至', '彼', '王', '百', '使', '奉', '勤', '蓋', '際']
txt_kinds19 = ['提', '般', '謂', '戒', '皆', '進', '弟', '壤', '漢', '野']
txt_kinds20 = ['令', '明', '德', '正', '修', '變', '樹', '畏', '好', '殺']
txt_kinds21 = ['非', '入', '出', '住', '丘', '底', '履', '疾', '威', '須']
txt_kinds22 = ['力', '地', '利', '持', '那', '開', '極', '獨', '息', '邪']
txt_kinds23 = ['九', '離', '當', '施', '釋', '手', '泥', '烏', '差', '廻']
txt_kinds24 = ['成', '復', '與', '欲', '或', '必', '障', '伏', '許', '誰']
txt_kinds25 = ['空', '引', '隨', '在', '解', '老', '議', '禮', '浮', '哉']
txt_kinds26 = ['語', '量', '合', '曰', '梵', '藥', '支', '夫', '擧', '竺']
txt_kinds27 = ['及', '事', '門', '念', '願', '失', '會', '首', '斯', '徒']
txt_kinds28 = ['神', '功', '日', '具', '迦', '益', '敬', '坐', '恒', '氣']
txt_kinds29 = ['悉', '從', '嚴', '光', '聞', '頭', '殊', '先', '設', '誦']
txt_kinds30 = ['今', '寶', '淸', '意', '伽', '句', '嚩', '財', '悲', '士']
txt_kinds31 = ['數', '尊', '樂', '某', '潙', '主', '城', '兩', '直', '立']
txt_kinds32 = ['同', '普', '本', '乃', '分', '矣', '億', '屬', '龍', '乞']
txt_kinds33 = ['足', '廣', '譯', '囉', '眞', '授', '玄', '少', '理', '太']
txt_kinds34 = ['便', '苦', '妙', '盡', '安', '還', '埵', '母', '槃', '命']
txt_kinds35 = ['性', '白', '華', '觀', '巳', '惱', '叉', '山', '告', '高']
txt_kinds36 = ['惡', '卽', '汝', '處', '已', '證', '形', '最', '賢', '周']
txt_kinds37 = ['根', '藏', '師', '滿', '常', '魔', '習', '壽', '遮', '貪']
txt_kinds38 = ['甲', '覺', '色', '然', '慧', '病', '增', '昧', '都', '遠']
txt_kinds39 = ['舍', '喜', '別', '陀', '深', '斷', '了', '退', '里', '品']
txt_kinds40 = ['轉', '業', '千', '則', '餘', '右', '雖', '照', '愛', '涅']
txt_kinds41 = ['滅', '緣', '忍', '長', '難', '趣', '眼', '報', '壬', '諦']
txt_kinds42 = ['海', '毘', '思', '金', '問', '圓', '陰', '初', '剛', '讚']
txt_kinds43 = ['張', '因', '起', '又', '罪', '南', '萬', '流', '文', '往']
txt_kinds44 = ['學', '護', '勝', '依', '向', '口', '小', '礙', '境', '娑']
txt_kinds45 = ['識', '聽', '捨', '耶', '下', '律', '內', '歸', '西', '答']
txt_kinds46 = ['磨', '後', '前', '間', '求', '平', '除', '攝', '靜', '止']
txt_kinds47 = ['女', '羯', '度', '犯', '聲', '闍', '哩', '就', '咤', '慈']
txt_kinds48 = ['去', '想', '化', '虛', '教', '虔', '俱', '函', '目', '取']
txt_kinds49 = ['過', '發', '未', '沙', '由', '彌', '雲', '稱', '次', '布']
txt_kinds50 = ['水', '字', '土', '果', '夜', '莫', '死', '動', '論', '歡']


def get_exam_names(size=50):
    names = []
    for i in range(1, size + 1):
        names.extend(eval('names%s' % i))
    return names


def get_exam_txt_kinds(size=50):
    names = []
    for i in range(1, size + 1):
        names.extend(eval('txt_kinds%s' % i))
    return names


def transform_box(box, mode='reduce,move'):
    if 'enlarge' in mode:
        box['w'] = round(box['w'] * 1.1, 1)
        box['h'] = round(box['h'] * 1.1, 1)
    if 'reduce' in mode:
        box['w'] = round(box['w'] * 0.8, 1)
        box['h'] = round(box['h'] * 0.8, 1)
    if 'move' in mode:
        box['x'] = box['x'] + int(box['w'] * 0.1)
        box['y'] = box['y'] + int(box['h'] * 0.1)


def add_random_column(boxes):
    random_box = boxes[random.randint(0, len(boxes) - 1)].copy()
    transform_box(random_box)
    max_cid = max([int(c.get('cid') or 0) for c in boxes])
    random_box['cid'] = max_cid + 1
    last = boxes[-1]
    random_box['column_id'] = 'b%sc%s' % (last['block_no'], last['column_no'] + 1)
    boxes.append(random_box)


def initial_bak_page(db):
    """ 设置备份数据"""
    pages = db.page.find({'bak': None})
    for p in pages:
        if not p.get('bak'):
            bak = {k: p.get(k) for k in ['blocks', 'columns', 'chars'] if p.get(k)}
            db.page.update_one({'_id': p['_id']}, {'$set': {'bak': bak}})


def reset_bak_page(db, names=None, data_type=None):
    """ 恢复数据"""
    condition = {}
    if names:
        condition = {'name': {'$in': names}}
    elif data_type == 'exam':
        condition = {'name': {'$in': get_exam_names()}}
    elif data_type == 'experience':
        condition = {'name': {'$regex': 'EX'}}
    pages = db.page.find(condition)
    for p in pages:
        if p.get('bak'):
            db.page.update_one({'_id': p['_id']}, {'$set': p['bak']})


def shuffle_exam_page(db, names=None):
    """ 处理考试数据：栏框进行放大或缩小，列框进行缩放和增删，字框进行缩放和增删"""
    names = names or get_exam_names()
    names = names.split(',') if isinstance(names, str) else names
    for i, name in enumerate(names):
        p = db.page.find_one({'name': name})
        print('processing %s' % name if p else '%s not existed' % name)
        assert len(p['chars']) > 10
        assert len(p['columns']) > 2
        mode = 'enlarge,move' if i % 2 else 'reduce,move'
        transform_box(p['blocks'][0], mode)
        transform_box(p['columns'][0], mode)
        transform_box(p['columns'][random.randint(0, len(p['columns']) - 1)], mode)
        add_random_column(p['columns'])
        transform_box(p['chars'][-1], mode)
        transform_box(p['chars'][random.randint(0, len(p['chars']) - 1)], mode)
        p['chars'].pop(random.randint(0, len(p['chars']) - 1))
        p['chars'].pop(random.randint(0, len(p['chars']) - 1))
        db.page.update_one({'_id': p['_id']}, {'$set': {k: p.get(k) for k in ['blocks', 'columns', 'chars']}})


def add_users(db, size=50):
    """ 创建考核以及练习账号"""
    users = []
    for i in range(1, size + 1):
        if db.user.find_one({'email': 'exam%02d@tripitakas.net' % i}, {'name': 1}):
            continue
        users.append({
            'name': '考核%02d' % i,
            'email': 'exam%02d@tripitakas.net' % i,
            'roles': "切分校对员,文字校对员,聚类校对员",
            'password': hp.gen_id('123abc'),
        })
    users.append({
        'name': '练习账号',
        'email': 'practice@tripitakas.net',
        'roles': "切分校对员,文字校对员,聚类校对员",
        'password': hp.gen_id('123abc'),
    })
    db.user.insert_many(users)


def publish_cut_proof_and_assign(db, size=50, num=1):
    """ 发布切分校对任务并进行指派"""

    def get_task(page_name, tsk_type, params=None, r_user=None):
        steps = Ph.prop(Ph.task_types, '%s.steps' % task_type)
        if steps:
            steps = {'todo': [s[0] for s in steps]}
        page = db.page.find_one({'name': page_name}, {'chars': 1})
        return dict(task_type=tsk_type, num=int(num), batch='考核任务', char_count=len(page['chars']),
                    collection='page', id_name='name', doc_id=page_name, status='picked',
                    steps=steps, priority=2, pre_tasks=None, params=params, result={},
                    create_time=Ph.now(), updated_time=Ph.now(), publish_time=Ph.now(),
                    publish_user_id=None, publish_by='管理员',
                    picked_user_id=r_user['_id'], picked_by=r_user['name'],
                    picked_time=Ph.now())

    print('publish cut_proof and assign')
    tasks = []
    task_type = 'cut_proof'
    # 创建考核任务并指派任务
    for i in range(1, size + 1):
        print('processing user %s' % i)
        user = db.user.find_one({'email': 'exam%02d@tripitakas.net' % i})
        for name in eval('names%s' % i):
            tasks.append(get_task(name, task_type, r_user=user))
    # 创建体验任务并指派任务
    user = db.user.find_one({'email': 'practice@tripitakas.net'})
    pages = list(db.page.find({'name': {'$regex': 'EX'}}, {'name': 1}))
    for p in pages:
        tasks.append(get_task(p['name'], task_type, r_user=user))
    db.task.insert_many(tasks)
    # 更新page的tasks状态
    db.page.update_many({'name': {'$regex': 'EX'}}, {'$set': {'tasks.%s.%s' % (task_type, num): 'picked'}})
    db.page.update_many({'name': {'$in': get_exam_names()}}, {'$set': {'tasks.%s.%s' % (task_type, num): 'picked'}})


def reset_cut_proof(db, user_no=None):
    """ 重置考核任务-切分校对"""
    # 重置账号相关的所有任务为picked
    print('reset cut_proof')
    cond = dict(task_type='cut_proof')
    cond['picked_by'] = '考核%2d' % user_no if user_no else {'$regex': '考核'}
    db.task.update_many(cond, {'$set': {'status': 'picked'}})
    db.task.update_many(cond, {'$unset': {
        'finished_time': '', 'steps.submitted': '', 'result.steps_finished': ''
    }})
    # 重置page的tasks字段
    tasks = list(db.task.find(cond, {'doc_id': 1}))
    db.page.update_many({'name': {'$in': [t['doc_id'] for t in tasks]}}, {'$set': {'tasks.cut_proof.1': 'picked'}})

    # 重置非系统指派的任务为published
    page_names = eval('names%s' % int(user_no)) if user_no else get_exam_names()
    cond['doc_id'] = {'$nin': page_names}
    db.task.update_many(cond, {'$set': {'status': 'published'}})
    db.task.update_many(cond, {'$unset': {
        'picked_time': '', 'picked_by': '', 'picked_user_id': '',
        'finished_time': '', 'steps.submitted': '', 'result.steps_finished': ''
    }})
    # 重置page的tasks字段
    tasks = db.task.find(cond, {'doc_id': 1})
    db.page.update_many({'name': {'$in': [t['doc_id'] for t in tasks]}}, {'$set': {'tasks.cut_proof.1': 'published'}})


def assign_cluster_proof(db, user_no=None):
    """ 指派聚类校对任务"""
    print('assign cluster_proof')
    task_type = 'cluster_proof'
    for i in range(1, 51):
        if not user_no or user_no == i:
            print('processing user %s' % i)
            txt_kinds = eval('txt_kinds%d' % i)
            cond = {'task_type': task_type, 'txt_kind': {'$in': txt_kinds}}
            user = db.user.find_one({'email': 'exam%02d@tripitakas.net' % int(i)})
            db.task.update_many(cond, {'$set': {
                'status': 'picked', 'picked_user_id': user['_id'], 'picked_by': user['name'],
                'picked_time': Ph.now(), 'updated_time': Ph.now(),
            }})
            db.task.update_many(cond, {'$unset': {
                'finished_time': '', 'steps.submitted': '', 'result.steps_finished': ''
            }})


def reset_cluster_proof(db, user_no=None):
    """ 重置考核任务-聚类校对"""
    # 重置账号相关的所有任务为picked
    print('reset cluster_proof')
    cond = dict(task_type='cluster_proof')
    cond['picked_by'] = '考核%2d' % user_no if user_no else {'$regex': '考核'}
    db.task.update_many(cond, {'$set': {'status': 'picked'}})
    db.task.update_many(cond, {'$unset': {
        'finished_time': '', 'steps.submitted': '', 'result.steps_finished': ''
    }})
    # 重置非系统指派的任务为published
    txt_kinds = eval('txt_kinds%s' % user_no) if user_no else get_exam_txt_kinds()
    cond['txt_kind'] = {'$nin': txt_kinds}
    db.task.update_many(cond, {'$set': {'status': 'published'}})
    db.task.update_many(cond, {'$unset': {
        'picked_time': '', 'picked_by': '', 'picked_user_id': '',
        'finished_time': '', 'steps.submitted': '', 'result.steps_finished': ''
    }})
    # 重置char表的txt字段
    print('reset char ocr_txt')
    for ocr_txt in txt_kinds:
        print('processing txt_kind %s' % ocr_txt)
        db.char.update_many({'ocr_txt': ocr_txt}, {'$set': {'txt': ocr_txt, 'txt_logs': [], 'tasks': {}}})
    # 清空用户新增的异体字
    print('delete variant added by users')
    db.variant.delete_many({'create_by': '考核%2d' % user_no if user_no else {'$regex': '考核'}})


def initial_run(db):
    """ 初始化"""
    # 针对所有page设置bak字段
    initial_bak_page(db)
    # 针对考核页面设置噪音
    shuffle_exam_page(db)
    # 创建用户
    add_users(db)
    # 发布切分校对并指派任务
    publish_cut_proof_and_assign(db)


def reset_user_data_and_tasks(db, user_no=None, admin_name=None):
    """ 重置体验数据、考核数据以及考核任务"""
    assert not user_no or user_no in range(1, 51)
    names = eval('names%s' % user_no) if user_no else None
    log = dict(user_no=user_no)
    _id = Bh.add_op_log(db, 'reset_exam', 'ongoing', log, admin_name)
    # 重置page数据
    reset_bak_page(db, names=names, data_type='exam')
    # 针对考核page设置噪音
    shuffle_exam_page(db, names)
    # 重置切分校对
    reset_cut_proof(db, user_no)
    # 重置聚类校对
    reset_cluster_proof(db, user_no)
    db.oplog.update_one({'_id': _id}, {'$set': {'status': 'finished'}})


def main(db=None, db_name=None, uri=None, func='reset_user_data_and_tasks', **kwargs):
    cfg = hp.load_config()
    db = db or (uri and pymongo.MongoClient(uri)[db_name]) or hp.connect_db(cfg['database'], db_name=db_name)[0]
    eval(func)(db, **kwargs)


if __name__ == '__main__':
    import fire

    fire.Fire(main)
