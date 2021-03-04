#!/usr/bin/env python
# -*- coding: utf-8 -*-
from tests.testcase import APITestCase
from controller.tool.diff import Diff
from controller.tool.rare import format_rare
from controller.tool.variant import normalize
from controller.page.base import PageHandler as Ph


class TestDiff(APITestCase):
    def setUp(self):
        super(TestDiff, self).setUp()
        self.add_first_user_as_admin_then_login()

    def test_utf8mb4(self):
        name = 'GL_1056_5_6'
        page = self._app.db.page.find_one({'name': name})
        ocr = page.get('ocr', '') + '卷北鿌沮渠蒙遜' + '\U0002e34f'
        self._app.db.page.update_one({'name': name}, {'$set': {'ocr': ocr}})
        page = self._app.db.page.find_one({'name': name})
        ocr = page.get('ocr', '')
        self.assertIn('卷北鿌沮渠蒙遜', ocr)
        self.assertIn('\U0002e34f', ocr)

    def test_format_rare(self):
        rare = '测[尸@工]试[仁-二+戾]一[少/兔]下[乳-孚+卓]看[束*束]看'
        txt = '测𡰱试㑦一㝹下𠃵看𣗥看'
        self.assertEqual(format_rare(rare), txt)

    def test_variant_normalize(self):
        variants = '鼶𪕬𪕧𪕽𪕻测𪕊𪕑䶅𪕘试𪕓𪕗看黑𪐫黒𪐗看'
        normal = normalize(variants)
        txt = '鼶鼶鼶鼶鼶測𪕊𪕊䶅䶅試𪕓𪕓看黑黑黑黑看'
        self.assertEqual(normal, txt)

    def test_merge_diff_pos(self):
        p1 = [(2, 4), (5, 5), (7, 9)]
        p2 = [(4, 5), (5, 5), (10, 10), (13, 15)]
        r = Diff._merge_diff_pos(p1, p2)
        self.assertEqual(r, [(2, 5), (5, 5), (7, 9), (10, 10), (13, 15)])

        p1 = [(2, 4), (5, 5), (7, 9)]
        p2 = [(4, 6), (10, 10), (13, 15)]
        r = Diff._merge_diff_pos(p1, p2)
        self.assertEqual(r, [(2, 6), (7, 9), (10, 10), (13, 15)])

        p1 = [(0, 1)]
        p2 = [(0, 17)]
        r = Diff._merge_diff_pos(p1, p2)
        self.assertEqual(r, [(0, 17)])

    def _assert_diff(self, diff, base, cmp1, cmp2=None, cmp3=None, label=None):
        lbl = dict(base='base', cmp1='cmp1', cmp2='cmp2', cmp3='cmp3')
        if label:
            lbl.update(label)

        # 检查文本没有遗漏
        base_str = Diff.pre_cmp(''.join([d[lbl['base']] for d in diff]))
        base = Diff.pre_cmp(base)
        self.assertEqual(base_str, base)

        cmp1_str = Diff.pre_cmp(''.join([d.get(lbl['cmp1'], '') for d in diff]))
        cmp1 = Diff.pre_cmp(cmp1)
        self.assertEqual(cmp1_str, cmp1)

        if cmp2:
            cmp2_str = Diff.pre_cmp(''.join([d.get(lbl['cmp2'], '') for d in diff]))
            cmp2 = Diff.pre_cmp(cmp2)
            self.assertEqual(cmp2_str, cmp2)

        if cmp3:
            cmp3_str = Diff.pre_cmp(''.join([d.get(lbl['cmp3'], '') for d in diff]))
            cmp3 = Diff.pre_cmp(cmp3)
            self.assertEqual(cmp3_str, cmp3)

    def test_diff_one_line(self):
        base = """天地玄黄宇  宙洪荒日月盈昃辰宿列张寒  来  暑  往秋收冬藏闰余成岁律吕调阳""".replace(' ', '')
        cmp1 = """天地改黄宇增宙洪  日月    辰宿改张寒增来  暑  往  收冬藏闰余成岁律吕调阳""".replace(' ', '')
        cmp2 = """天地变黄宇加宙洪  日月    辰宿列变寒  来加暑  往秋  冬藏闰余成岁律吕调阳""".replace(' ', '')
        cmp3 = """天地更黄宇附宙洪  日月    辰更列张寒  来  暑附往秋收  藏闰余成岁律吕调阳""".replace(' ', '')
        ret1, err1 = Diff.diff(base, cmp1, label=dict(cmp1='cmp1'))
        ret2, err2 = Diff.diff(base, cmp2, label=dict(cmp1='cmp2'))
        ret3, err3 = Diff.diff(base, cmp3, label=dict(cmp1='cmp3'))

        ret12, err12 = Diff._merge_by_combine(ret1, ret2)
        self.assertEqual(len(ret12), 18)
        base_str = ''.join([d['base'] for d in ret12 if d['base'] != '\n'])
        self.assertEqual(base_str, base)

        r12, e12 = Diff.diff(base, cmp1, cmp2)
        self.assertEqual(len(r12), 18)
        base_str = ''.join([d['base'] for d in r12 if d['base'] != '\n'])
        self.assertEqual(base_str, base)

        ret123, err12 = Diff._merge_by_combine(ret12, ret3)
        self.assertEqual(len(ret123), 20)
        base_str = ''.join([d['base'] for d in ret123 if d['base'] != '\n'])
        self.assertEqual(base_str, base)

        r123, e123 = Diff.diff(base, cmp1, cmp2, cmp3)
        self.assertEqual(len(r123), 20)
        base_str = ''.join([d['base'] for d in r123 if d['base'] != '\n'])
        self.assertEqual(base_str, base)

    def test_diff_lines(self):
        base_lines = """
        2.天地玄黄宇宙洪荒日月盈昃辰宿列张
        3.寒来暑往秋收冬藏闰余成岁律吕调阳
        4.云腾致雨露结为霜金生丽水玉出昆冈
        5.剑号巨阙珠称夜光果珍李柰菜重芥姜
        6.海咸河淡鳞潜羽翔龙师火帝鸟官人皇
        7.始制文字乃服衣裳推位让国有虞陶唐
        8.吊民伐罪周发殷汤坐朝问道垂拱平章
        9.爱育黎首臣伏戎羌遐迩一体率宾归王
        10.鸣凤在竹白驹食场化被草木赖及万方""".replace('        ', '')

        cmp_lines1 = """
        2.天地改黄宇增宙洪日月辰宿改张
        3.
        4.云腾致雨露结为霜金生丽水玉出昆冈
        5.剑号巨阙珠称夜光果珍李柰菜重芥姜始制文字乃服衣裳推位让国有虞陶唐
        6.海咸河淡鳞潜羽翔龙师火帝鸟官人皇
        7.始制文字乃服衣裳推位让国有虞陶唐女慕贞洁男效才良知过必改得能莫忘
        8.吊民伐罪周发殷汤坐朝问道垂拱平章
        9.爱育黎首臣伏戎羌遐迩一体率宾归王
        10.鸣凤在竹白驹食场化被草木赖及万方""".replace('        ', '')

        cmp_lines2 = """
        2.天地变黄宇加宙洪日月辰宿列变
        3.
        4.云腾致雨露结为霜金生丽水玉出昆冈
        5.剑号巨阙珠称夜光果珍李柰菜重芥姜始制文字乃服衣裳推位让国有虞陶唐
        6.海咸河淡鳞潜羽翔龙师火帝鸟官人皇
        7.始制文字乃服衣裳推位让国有虞陶唐
        8.吊民伐罪周发殷汤坐朝问道垂拱平章女慕贞洁男效才良知过必改得能莫忘
        9.爱育黎首臣伏戎羌遐迩一体率宾归王
        10.鸣凤在竹白驹食场化被草木赖及万方""".replace('        ', '')

        cmp_lines3 = """
        2.天地更黄宇附宙洪日月辰更列张
        3.
        4.云腾致雨露结为霜金生丽水玉出昆冈
        5.剑号巨阙珠称夜光果珍李柰菜重芥姜始制文字乃服衣裳推位让国有虞陶唐
        6.海咸河淡鳞潜羽翔龙师火帝鸟官人皇
        7.始制文字乃服衣裳推位让国有虞陶唐
        8.吊民伐罪周发殷汤坐朝问道垂拱平章
        9.爱育黎首臣伏戎羌遐迩一体率宾归王女慕贞洁男效才良知过必改得能莫忘
        10.鸣凤在竹白驹食场化被草木赖及万方""".replace('        ', '')

        ret1, err1 = Diff.diff(base_lines, cmp_lines1, label=dict(cmp1='cmp1'))
        self._assert_diff(ret1, base_lines, cmp_lines1)

        ret2, err2 = Diff.diff(base_lines, cmp_lines2, label=dict(cmp1='cmp2'))
        self._assert_diff(ret2, base_lines, cmp_lines2, label=dict(cmp1='cmp2'))

        ret3, err3 = Diff.diff(base_lines, cmp_lines3, label=dict(cmp1='cmp3'))
        self._assert_diff(ret3, base_lines, cmp_lines3, label=dict(cmp1='cmp3'))

        ret12, err12 = Diff._merge_by_combine(ret1, ret2)
        self._assert_diff(ret12, base_lines, cmp_lines1, cmp_lines2)

        r12, e12 = Diff.diff(base_lines, cmp_lines1, cmp_lines2)
        self._assert_diff(r12, base_lines, cmp_lines1, cmp_lines2)

        ret123, err12 = Diff._merge_by_combine(ret12, ret3)
        self._assert_diff(ret123, base_lines, cmp_lines1, cmp_lines2, cmp_lines3)

        r123, e123 = Diff.diff(base_lines, cmp_lines1, cmp_lines2, cmp_lines3)
        self._assert_diff(r123, base_lines, cmp_lines1, cmp_lines2, cmp_lines3)

    def test_page_diff(self):
        # QL_4_629
        ocr = "般若波羅蜜多復次舍利子菩薩摩訶薩不|爲引發苦聖諦故應引發般若波羅蜜多不|爲引發集滅道聖諦故應引發般若波羅蜜|多世尊云何菩薩摩訶薩不爲引發苦聖諦|故應引發般若波羅蜜多不爲引發集滅道|聖諦故應引發般若波羅蜜多舍利子以苦|聖諦無作無止無生無滅無成無壞無得無|捨無自性故菩薩摩訶薩不爲引發苦聖諦|故應引發般若波羅蜜多以集滅道聖諦無|作無止無生無滅無成無壞無得無捨無自|性故菩薩摩訶薩不爲引發集滅道聖諦故|應引發般若波羅蜜多復次舍利子菩薩摩|訶薩不爲引發四靜慮故應引發般若波羅|蜜多不爲引發四無量四無色定故應引發|般若波羅蜜多世尊云何菩薩摩訶薩不爲||引發四靜慮故應引發般若波羅蜜多不爲|引發四無量四無色定故應引發般若波羅|蜜多舍利子以四靜慮無作無止無生無滅|無成無壞無得無捨無自性故菩薩摩訶薩|不爲引發四靜慮故應引發般若波羅蜜多|以四無量四無色定無作無止無生無滅無|成無壞無得無捨無自性故菩薩摩訶薩不|爲引發四無量四無色定故應引發般若波|羅蜜多|大般若波羅蜜多經卷第一百七十二|音釋|矜店御切頸矜也蔑彌列叨轉易也設利羅梵捂也亦壬室利罹又云|舍利北云骨身又云靈骨窣堵波梵諱也北云方墳又云圃罤帛春沒切堵|昔狁瞖眩醫肯翁目疾也洶音縣刑熏常生也"
        ocr_col = "般若波羅蜜多復次舎利子菩薩摩訶薩不|爲引發苦聖諦故應引發般若波羅蜜多不|爲引發集滅道聖諦故應引發般若波羅蜜|多世尊云何菩薩摩訶薩不爲引發苦聖諦|故應引發般若波羅蜜多不爲引發集滅道|聖諦故應引發般若波羅蜜多舎利子以苦|聖諦無作無止無生無滅無成無壞無得無|捨無自性故菩薩摩訶薩不爲引發苦聖諦|故應引發般若波羅蜜多以集滅道聖諦無|作無止生無滅無成無壞無得無捨無自|性故菩薩摩訶薩不爲引發集滅道聖諦故|應引發般若波羅蜜多復次舎利子菩薩摩|薩不爲引發四靜故應引發般若波羅|蜜多不爲引發四無量四無色定故應引發|般若波羅蜜多世尊云何菩薩摩訶薩不爲||引四靜慮故應引發般若波羅蜜多不爲|引發四無量四無色定故應引發般若波羅|蜜多舎利子以四靜慮無作無止無生無滅|無成無壞無得無捨無自性故菩薩摩訶薩|不爲引發四靜慮故應引發般若波羅蜜多|以四量四無色定無作無止無生無滅無|成無壞無得無捨無自性故菩薩摩訶薩不|爲引發四無量四無色定故應引發般若波|羅蜜多|大般若波羅蜜多經卷第一百七十二|音釋|子増隱間以設利羅覺離二經|捨是雲能窣者波提攝也說汝般|諸譬敢訶經離"
        cmp = "般若波羅蜜多復次舍利子菩薩摩訶薩不為引發苦聖諦故應引發般若波羅蜜多不為引發集滅道聖諦故應引發般若波羅蜜多世尊云何菩薩摩訶薩不為引發苦聖諦故應引發般若波羅蜜多不為引發集滅道聖諦故應引發般若波羅蜜多舍利子以苦聖諦無作無止無生無滅無成無壞無得無捨無自性故菩薩摩訶薩不為引發苦聖諦故應引發般若波羅蜜多以集滅道聖諦無作無止無生無滅無成無壞無得無捨無自性故菩薩摩訶薩不為引發集滅道聖諦故應引發般若波羅蜜多復次舍利子菩薩摩訶薩不為引發四靜慮故應引發般若波羅蜜多不為引發四無量四無色定故應引發般若波羅蜜多世尊云何菩薩摩訶薩不為引發四靜慮故應引發般若波羅蜜多不為引發四無量四無色定故應引發般若波羅蜜多舍利子以四靜慮無作無止無生無滅無成無壞無得無捨無自性故菩薩摩訶薩不為引發四靜慮故應引發般若波羅蜜多以四無量四無色定無作無止無生無滅無成無壞無得無捨無自性故菩薩摩訶薩不為引發四無量四無色定故應引發般若波羅蜜多大般若波羅蜜多經卷第一百七十二"
        segments = Ph.diff(ocr, ocr_col, cmp)
        self.assertTrue(segments)

        # QL_25_313
        base = '子我等二人但能知此菩薩解脫如諸菩薩|摩訶薩善入無邊諸事幻網彼功德行我等|云何能知能說時童子童女說自解脫已諸|善根力不思議故令善財身柔輭光澤賢首藏師|探玄記云自下九位知識皆是舊翻于闐本所欠應是西域覺賢之所畧耳余共日照三|垂八 十三|藏勘天竺諸本及崐崙本并于闐別行本並皆同有此欠是以於大唐永隆年西京西太|原寺三藏法師地婆訶羅唐云日照共京十大德道成律師等奉勑譯補沙門復禮親從|筆受自說本願又作是言善男子於此南方有|一國土名曰海澗彼有園林名大莊嚴藏於|彼林中有大樓觀名嚴淨藏菩薩往昔善根|所起菩薩諸願自在諸通智力巧妙方便功|德大悲法門所起彼園中有菩薩摩訶薩名|曰彌勒常化父母親戚眷屬及同行者又復|長養其餘無量衆生善根令住大乗亦欲爲|汝顯現菩薩方便法門欲明菩薩受生自在|||欲對現教化一切衆生令猒諸有宣明菩薩|大慈悲力覺悟菩薩無相法門明諸有趣悉|無自相汝詣彼問云何菩薩淨菩薩道云何|菩薩學菩薩戒云何菩薩淨菩薩心云何菩|薩發諸大願云何菩薩積功德具云何菩薩|得菩薩地云何菩薩滿足一切諸波羅蜜云|何菩薩得諸忍法云何菩薩住功德行云何|菩薩近善知識何以故彼菩薩摩訶薩究竟|一切諸菩薩行分別了知衆生心行以巧便|智而教化之滿足一切諸波羅蜜住菩薩地|得諸忍門證於菩薩離生之法於諸佛所而|得受記於菩薩法自在遊戲持諸佛持無量|諸佛以一切智甘露正法而灌其頂善男子|彼菩薩摩訶薩能示導汝真善知識堅菩提|心長養善根住正直心現菩薩根說無礙法'
        cmp = '子我等二人但能知此菩薩解脫如諸菩薩摩訶薩善入無邊諸事幻網彼功德行我等云何能知能說時童子童女說自解脫已諸善根力不思議故令善財身柔軟光澤自說本願大方廣佛華嚴經卷第五十七大方廣佛華嚴經卷第五十八東晉天竺三藏佛馱跋陀羅譯入法界品第三十四之十五又作是言善男子於此南方有一國土名曰海㵎彼有園林名大莊嚴藏於彼林中有大樓觀名嚴淨藏菩薩往昔善根所起菩薩諸願自在諸通智力巧妙方便功德大悲法門所起彼園中有菩薩摩訶薩名曰彌勒常化父母親戚眷屬及同行者又復長養其餘無量眾生善根令住大乘亦欲為汝顯現菩薩方便法門欲明菩薩受生自在欲對現教化一切眾生令厭諸有宣明菩薩大慈悲力覺悟菩薩無相法門明諸有趣悉無自相汝詣彼問云何菩薩淨菩薩道云何菩薩學菩薩戒云何菩薩淨菩薩心云何菩薩發諸大願云何菩薩積功德具云何菩薩得菩薩地云何菩薩滿足一切諸波羅蜜云何菩薩得諸忍法云何菩薩住功德行云何菩薩近善知識何以故彼菩薩摩訶薩究竟一切諸菩薩行分別了知眾生心行以巧便智而教化之滿足一切諸波羅蜜住菩薩地得諸忍門證於菩薩離生之法於諸佛所而得授記於菩薩法自在遊戲持諸佛持無量諸佛以一切智甘露正法而灌其頂善男子彼菩薩摩訶薩能示導汝真善知識堅菩提心長養善根住正直心現菩薩根說無礙法'
        segments = Ph.diff(base, cmp)
        self.assertTrue(segments)

    def test_diff_api(self):
        data = {
            'texts': [
                "說偈只這些兒住處是吾生長之地增加几个字別去三十七|年日月疾如彈指政和元年辛卯持缽至紹興七年丁巳計二十七年走遍|天下叢林意圖出離生死報答父母重恩不是等|閑遊戲平生得固剛強方與佛祖出氣今朝依旧|還鄉親戚百無一二道是昔人猶非道非昔人猶|是莫作是非論量透過世間出世慇懃普勸諸人|急著眼睛看取东持钵鄰郡訪雙槐居士鄭禹功|於璉市作佛燈珣禪師真讚金華聖者畫像讚題|吳氏六湛堂|八午|師五十歲乃入院之明年眾將一千皆諸方角立",
                "說偈只這些兒住處是吾生長之地別去二十七年日月疾如彈指政和元年辛卯持缽至紹興七年丁巳計二十七年走遍天下叢林意圖出離生死報答父母重恩不是等閑遊戲平生得箇剛強方與佛祖出氣今朝依舊還鄉親戚百無一二道是昔人猶非道非昔人猶是莫作是非論量透過世間出世慇懃普勸諸人急著眼睛看取冬持缽鄰郡訪雙槐居士鄭禹功於璉市作佛燈珣禪師真讚金華聖者畫像讚題吳氏六湛堂八年戊午師五十歲乃入院之明年眾將一千皆諸方角立",
            ],
            'hints': [
                {"block_no": 1, "line_no": 1, "base": "三", "cmp1": "二", "offset": "16"},
                {"block_no": 1, "line_no": 4, "base": "固", "cmp1": "箇", "offset": "6"},
                {"block_no": 1, "line_no": 4, "base": "旧", "cmp1": "舊", "offset": "18"},
            ]
        }
        data = {
            "texts": [
                "數世界有世界名清淨須彌音佛號出現一|切行光明此上過佛剎微塵數世界有世界|名香水蓋佛號一切波羅蜜無礙海此上過|佛剎微塵數世界有世界名師子華網佛號|寳燄幢此上過佛剎微塵數世界有世界名|金剛妙華燈佛號一切大願光此上過佛剎|微塵數世界有世界名一切法光明地佛號|一切法廣大真實義此上過佛剎微塵數世|界有世界名真珠末平坦莊嚴佛號勝慧光|明網此上過佛剎微塵數世界有世界名瑠|璃華佛號寶積幢此上過佛剎微塵數世界|有世界名無量妙光輪佛號大威力智海藏|此上過佛剎微塵數世界有世界名明見十|方佛號淨修一切功德幢此上過佛剎微塵|數世界有世界名可愛樂梵音形如佛手依||拱九七|寶光網海住菩薩身一切莊嚴雲而覆其上|二十佛剎微塵數世界圍繞純一清淨佛號|普照法界無礙光|||",
                "數世界有世界名清淨須彌音佛號出現不|切行光明此上過佛刹微塵數世界有世界|名香蓋佛號一切波羅蜜無礙海此上過|佛刹微塵數世界有世界名師子華佛遍|寳燄幢此上過佛刹微塵數世界有世界名|金剛妙華燈佛號一切大願光此上過佛刹|微塵數世界有世界名一切法光明地佛號|一切法廣大眞實義此上過佛刹微塵數世|界有世界名眞珠末平世莊嚴佛號勝慧光|明網此上過佛刹微塵數世界有世界名増|璃華佛號寳積幢此上過佛刹微塵數世界|有世界名無量妙光輪佛號大威力智海藏|此上過佛刹微塵數世界有世界名眀見十|方佛號淨修一切功德幢此上過佛刹微塵|數世界有世界名可愛樂梵音淨如佛手依||供九百|寳光網海住菩薩身一切莊嚴雲而覆其上|二十刹微塵數世界圍繞純一清淨佛號|普照法界無礙光|大方廣佛華嚴經卷第九|音釋|廣習怨地寳集増道||",
                "數世界有世界名清淨須彌音佛號出現一|切行光明此上過佛剎微塵數世界有世界|名香水蓋佛號一切波羅蜜無礙海此上過|佛剎微塵數世界有世界名師子華網佛號|寶𦦨幢此上過佛剎微塵數世界有世界名|金剛妙華燈佛號一切大願光此上過佛剎|微塵數世界有世界名一切法光明地佛號|一切法廣大真實義此上過佛剎微塵數世|界有世界名真珠末平坦莊嚴佛號勝慧光|明網此上過佛剎微塵數世界有世界名瑠|璃華佛號寶積幢此上過佛剎微塵數世界|有世界名無量妙光輪佛號大威力智海藏|此上過佛剎微塵數世界有世界名明見十|方佛號淨修一切功德幢此上過佛剎微塵|數世界有世界名可愛樂梵音形如佛手依|寶光網海住菩薩身一切莊嚴雲而覆其上|二十佛剎微塵數世界圍繞純一清淨佛號|普照法界無礙光|"
            ],
            "hints": [
            ]
        }

        r = self.fetch('/api/page/txt/diff', body={'data': data})
        d = self.parse_response(r)
        self.assert_code(200, r)
