/**
 * 框序校对
 * Date: 2020-12-16
 */
(function () {
  'use strict';

  $.box.onBoxChanged(function (box, reason, param) {
    if (reason === 'switch') {
      $.box.switchCurLink(null, box);
    }
  });

  let self = $.box;
  let data = self.data;
  let status = self.status;
  let oStatus = {
    hasChanged: false,                              // 用户是否已修改
    isMouseDown: false,                             // 鼠标左键是否按下
    isDragging: false,                              // 鼠标是否在点击拖拽
    downPt: null,                                   // 点击的坐标
    curCap: null,                                   // 当前控制帽
    dragLink: null,                                 // 当前拖拽的序线
    curLinkType: null,                              // 当前序线的类型
    curLink: {box: null, side: null, link: null},   // 当前修改的序线
    hasInit: null,                                  // 序线是否已初始化
    showBackBox: false,                             // 是否显示背景底框
    userLinks: {},                                  // 用户修改的序线
  };

  $.extend($.box, {
    oStatus: oStatus,
    initOrder: initOrder,
    toggleLink: toggleLink,
    drawLink: drawLink,
    checkLinks: checkLinks,
    isOrderMode: isOrderMode,
    reorderBoxes: reorderBoxes,
    loadUserLinks: loadUserLinks,
    deleteCurLink: deleteCurLink,
    switchCurLink: switchCurLink,
    updateUserLinks: updateUserLinks,
    updateNoByLinks: updateNoByLinks,
  });

  function isOrderMode() {
    return status.boxMode === 'order';
  }

  function initOrder(p) {
    if (p && p.userLinks) oStatus.userLinks = p.userLinks;
    // bind event
    $(data.holder).find('svg').on('mousedown', mouseDown).mouseup(mouseUp).mousemove(function (e) {
      if (!oStatus.isMouseDown) mouseHover(e);
      else if (self.getDistance(self.getPoint(e), oStatus.downPt) > data.ratio) //仅当拖拽距离大于1时才触发拖拽函数
        mouseDrag(e);
    });
  }

  function switchCurLink(pt, box) {
    self.removeClass(oStatus.curLink.link, 'hover');
    if (!oStatus.curLinkType) return;
    box = box || self.findBoxByPoint(pt, oStatus.curLinkType, notDeleted);
    if (!box) return;
    let side = pt ? switchCap(box, pt) : switchCap(box, null, 'out');
    let link = getLink(box, side);
    self.addClass(link, 'hover');
    oStatus.curLink = {box: box, side: side, link: link};
  }

  function mouseHover(e) {
    if (!isOrderMode() || status.readonly) return;
    e.preventDefault();
    switchCurLink(self.getPoint(e));
  }

  function mouseDown(e) {
    if (!isOrderMode() || status.readonly) return;
    e.preventDefault();
    if (e.button === 2) return; // 鼠标右键
    oStatus.downPt = self.getPoint(e);
    let box = self.findBoxByPoint(oStatus.downPt, status.curBoxType, notDeleted);
    self.switchCurBox(box);
    switchCurLink(oStatus.downPt);
    oStatus.isDragging = false;
    oStatus.isMouseDown = true;
  }

  function mouseDrag(e) {
    if (!isOrderMode() || status.readonly) return;
    e.preventDefault();
    if (!oStatus.curCap) return;
    // init
    oStatus.isDragging = true;
    oStatus.dragPt = self.getPoint(e);
    let cls = oStatus.curCap.attr('class');
    oStatus.curCap && oStatus.curCap.remove();
    oStatus.curCap = createCap(oStatus.dragPt, cls);
    let box = oStatus.curLink.box;
    let cls1 = 'link dragging ln-' + box.boxType;
    oStatus.dragLink && oStatus.dragLink.remove();
    if (self.hasClass(oStatus.curCap, 'out')) { // 1.当前为出点
      let link = box && box.outLink;
      if (link && link.elem) { // 1.1当前框有序线，则修改序线
        self.addClass(link.elem, 'on-drag');
        let box2 = link.in;
        let pt2 = getCapPt(box2, box2.boxType, 'in');
        oStatus.dragLink = createLink(oStatus.dragPt, pt2, cls1);
      } else { // 1.2当前框无序线，则画新序线
        let pt1 = getCapPt(box, box.boxType, 'out');
        oStatus.dragLink = createLink(pt1, oStatus.dragPt, cls1);
      }
    } else {  // 2.当前为入点
      let link = box && box.inLink;
      if (link && link.elem) { // 1.1当前框有序线，则修改序线
        self.addClass(link.elem, 'on-drag');
        let box1 = link.out;
        let pt1 = getCapPt(box1, box1.boxType, 'out');
        oStatus.dragLink = createLink(pt1, oStatus.dragPt, cls1);
      } else { // 1.2当前框无序线，则画新序线
        let pt2 = getCapPt(box, box.boxType, 'in');
        oStatus.dragLink = createLink(oStatus.dragPt, pt2, cls1);
      }
    }
  }

  function mouseUp(e) {
    function onQuit() {
      self.removeClass(oStatus.curLink.link, 'on-drag');
      oStatus.dragLink && oStatus.dragLink.remove();
      oStatus.isDragging = false;
      oStatus.dragLink = null;
    }

    function check(a, sideA, b, isUpdate) {
      // 1.是否同一个框
      if (a.idx === b.idx) return false;
      // 2.是否同一种框
      if (a.boxType !== b.boxType) return false;
      // 3.检查栏列号，跳过新增的字框（未分配栏列号）
      if (a.boxType === 'char' && a.block_no && b.block_no && a.column_no && b.column_no && (
          a.block_no !== b.block_no || a.column_no !== b.column_no)) {
        bsShow('提示', '两个字框不在同一列，禁止连接', 'warning', 2000);
        return false;
      } else if (a.boxType === 'column' && a.block_no && b.block_no && a.block_no !== b.block_no) {
        bsShow('提示', '两个列框不在同一栏，禁止连接', 'warning', 2000);
        return false;
      }
      // 4.检查目标框的连线
      let sideB = isUpdate ? sideA : {in: 'out', out: 'in'}[sideA];
      if (b[sideB + 'Link']) {
        bsShow('提示', '目标框' + {in: '入', out: '出'}[sideB] + '点已有连线', 'warning', 2000);
        return false;
      }
      return true;
    }

    function cancelLink(box, side) {
      let link = box[side + 'Link'];
      link && link.elem && link.elem.remove();
      box[side + 'Link'] = null;
      oStatus.hasChanged = true;
    }

    if (!isOrderMode() || status.readonly) return;
    e.preventDefault();
    oStatus.isMouseDown = false;
    if (!oStatus.isDragging) return onQuit();
    let side = oStatus.curLink.side;
    let srcBox = oStatus.curLink.box;
    let isUpdate = !!getLink(srcBox, side);
    let pt = self.getPoint(e);
    let dstBox = self.findBoxByPoint(pt, oStatus.curLinkType, notDeleted);
    if (!dstBox || !check(srcBox, side, dstBox, isUpdate)) return onQuit();
    // draw link
    let p = {out: null, in: null};
    if (isUpdate) {
      if (side === 'out') Object.assign(p, {out: dstBox, in: srcBox.outLink.in});
      else Object.assign(p, {out: srcBox.inLink.out, in: dstBox});
      if (p.out.idx === p.in.idx) return onQuit();
      cancelLink(srcBox, side);
    } else {
      if (side === 'out') Object.assign(p, {out: srcBox, in: dstBox});
      else Object.assign(p, {out: dstBox, in: srcBox});
    }
    setLink(p.out, p.in);
    oStatus.hasChanged = true;
    onQuit();
  }

  function notDeleted(box) {
    return box.op !== 'deleted' && (!box.deleted || box.op === 'recovered');
  }

  function getCapPt(elem, boxType, side) {
    if (elem && elem.elem) elem = elem.elem;
    let b = elem.getBBox();
    if (boxType === 'char') { // 右出左进
      if (side === 'out') return {x: b.x + b.width * 0.75, y: b.y + b.height * 0.5};
      if (side === 'in') return {x: b.x + b.width * 0.25, y: b.y + b.height * 0.5};
    }
    if (boxType === 'column') { // 上进下出
      if (side === 'out') return {x: b.x + b.width * 0.5, y: b.y + b.height * 0.75};
      if (side === 'in') return {x: b.x + b.width * 0.5, y: b.y + b.height * 0.25};
    }
    if (boxType === 'block') { // 右出左进
      if (side === 'out') return {x: b.x + b.width * 0.75, y: b.y + b.height * 0.5};
      if (side === 'in') return {x: b.x + b.width * 0.25, y: b.y + b.height * 0.5};
    }
  }

  function createCap(pt, cls) {
    if (!pt) return;
    let r = 5 * Math.min(data.ratio, 1.5); // 控制点的半径
    return data.paper.circle(pt.x, pt.y, r).attr({'class': cls});
  }

  function switchCap(box, pt, side) {
    oStatus.curCap && oStatus.curCap.remove();
    if (!box || !box.elem) return;
    side = side || getSide(box, pt);
    let lt = getCapPt(box.elem, box.boxType, side);
    oStatus.curCap = createCap(lt, 'cap cp-' + box.boxType + ' ' + side);
    return side;
  }

  function getSide(box, pt) {
    let b = box.elem.getBBox(), side = '';
    if (box.boxType === 'char') side = pt.x < b.x + b.width / 2 ? 'in' : 'out';
    if (box.boxType === 'column') side = pt.y < b.y + b.height / 2 ? 'in' : 'out';
    if (box.boxType === 'block') side = pt.x < b.x + b.width / 2 ? 'in' : 'out';
    return side;
  }

  function getLink(box, side, opposite) {
    if (!box) return;
    if (side === 'in') return opposite ? box.outLink : box.inLink;
    if (side === 'out') return opposite ? box.inLink : box.outLink;
  }

  function deleteLink(link, side) {
    if (!link) return;
    link.elem && link.elem.remove();
    if (!side || side === 'in') link.in.inLink = null;
    if (!side || side === 'out') link.out.outLink = null;
  }

  function deleteCurLink() {
    deleteLink(oStatus.curLink.link);
    return oStatus.curLink.link.in;
  }

  function drawLink(reset) {
    if (oStatus.hasInit && !reset) return;
    let prev = {block: null, column: null, char: null};
    data.boxes.forEach(function (b, i) {
      if (self.isDeleted(b)) return deleteLink(b.inLink);
      let a = prev[b.boxType];
      if (a) a.iniOutCid = setLink(a, b) ? b.cid : null;
      if (!a || !a.iniOutCid) deleteLink(b.inLink); // b是第一个框
      prev[b.boxType] = b;
    });
    oStatus.hasInit = true;
  }

  function setLink(a, b) {
    let r = data.ratio;
    let boxType = a.boxType;
    if ((boxType === 'char' && (a['block_no'] !== b['block_no'] || a['column_no'] !== b['column_no'])) ||
        (boxType === 'column' && a['block_no'] !== b['block_no'])) {
      deleteLink(a.outLink, 'out');
      deleteLink(b.inLink, 'in');
      return false;
    }
    let pt = a.outLink && a.outLink.elem && a.outLink.elem.attr('path');
    let ap = getCapPt(a, boxType, 'out'), bp = getCapPt(b, boxType, 'in');
    if (pt && a.outLink.in.cid === b.cid) {
      let x = ap.x / r, y = ap.y / r, x1 = bp.x / r, y1 = bp.y / r;
      if (pt[0][1] === x && pt[0][2] === y && pt[1][1] === x1 && pt[1][2] === y1)
        return true;
    }
    a.outLink && a.outLink.elem && a.outLink.elem.remove();
    b.inLink && b.inLink.elem && b.inLink.elem.remove();

    let s = Math.sqrt(a.elem.attrs.width * a.elem.attrs.height);
    s = s > 40 ? 40 : s < 10 ? 10 : s; // 面积从10~40，对应连线宽度从0.8到2
    let w = (0.8 + (s - 10) * 0.04) * r;
    let p = {column: 'block_no', char: 'column_no'};
    let even = a[p[boxType]] % 2 ? ' odd' : ' even';
    let link = createLink(ap, bp, 'link ln-' + boxType + even).attr({
      'id': a.idx + '#' + b.idx, 'stroke-width': w,
    });
    a.outLink = b.inLink = {elem: link, out: a, in: b};
    return true;
  }

  function createLink(fromPt, toPt, cls) {
    let r = data.ratio;
    return data.paper.path('M' + fromPt.x / r + ',' + fromPt.y / r + 'L' + toPt.x / r + ',' + toPt.y / r)
        .attr({'class': cls}).initZoom(1).setZoom(r);
  }

  function updateUserLinks() {
    let links = oStatus.userLinks;
    self.data.boxes.forEach((b) => {
      if (b.outLink) {
        if (!b.iniOutCid) // 新增
          links[b.boxType + '_' + b.cid] = b.outLink.in.cid;
        else if (b.iniOutCid !== b.outLink.in.cid) // 修改
          links[b.boxType + '_' + b.cid] = b.outLink.in.cid;
      } else {
        if (b.iniOutCid) // 删除
          links[b.boxType + '_' + b.cid] = null;
      }
    });
    return links;
  }

  function loadUserLinks() {
    function updateNoAndId(boxType, from, to, no) {
      for (let i = from; i <= to; i++) { // 先分类
        let b = self.data.boxes[i];
        if (self.isDeleted(b)) continue;
        if (boxType === 'column') {
          b.subBoxes = self.data.boxes.filter((c) => c.boxType === 'char' && c['block_no'] === b['block_no']
              && c['column_no'] === b['column_no']);
        } else if (boxType === 'block') {
          b.subBoxes = self.data.boxes.filter((c) => (c.boxType === 'char' || c.boxType === 'column')
              && c['block_no'] === b['block_no']);
        }
      }
      for (let i = from; i <= to; i++) { // 后赋值
        let b = self.data.boxes[i];
        if (self.isDeleted(b)) continue;
        b.subBoxes && b.subBoxes.forEach((c) => {
          c[boxType + '_no'] = no;
          c[c.boxType + '_id'] = self.getBoxId(c);

        });
        b[boxType + '_no'] = no;
        b[b.boxType + '_id'] = self.getBoxId(b);
        no++;
      }
    }

    function getLinkMeta(outKey, inCid) {
      let a = outKey.split('_');
      let boxType = a[0], outCid = parseInt(a[1]);
      let outIdx = null, inIdx = null;
      for (let i = 0, len = self.data.boxes.length; i < len; i++) {
        let c = self.data.boxes[i];
        if (c.boxType === boxType && c.cid === inCid) inIdx = i;
        if (c.boxType === boxType && c.cid === outCid) outIdx = i;
        if (outIdx !== null && inIdx !== null) break;
      }
      return {boxType: boxType, outIdx: outIdx, outCid: outCid, inIdx: inIdx, inCid: inCid}
    }

    let links = Object.assign({}, oStatus.userLinks);
    if (!links || !Object.keys(links).length) return;
    for (let key in links) {
      if (!links[key]) continue;
      let m = getLinkMeta(key, links[key]);
      if (m.inIdx > m.outIdx) continue;
      let inBox = self.data.boxes[m.inIdx], outBox = self.data.boxes[m.outIdx];
      if (self.isDeleted(inBox) || self.isDeleted(outBox)) continue;
      for (let key2 in links) {   // 查找配对序线
        if (key2 === key || !links[key2] || key2.split('_')[0] !== m.boxType) continue;
        let m2 = getLinkMeta(key2, links[key2]);
        if (m2.inIdx === m.outIdx + 1) {
          // 将[m.outIdx, m2.inIdx]区间的元素往后移动，插入到m2.inIdx之后、m.outIdx之前
          let size = m2.outIdx - m.inIdx + 1;
          let startNo = inBox[m.boxType + '_no'];
          let items = self.data.boxes.splice(m.inIdx, size);
          self.data.boxes.splice(m2.inIdx - size, 0, ...items);
          updateNoAndId(m.boxType, m.inIdx, m2.inIdx - 1, startNo);
          links[key] = links[key2] = null;
          break;
        } else if (m2.outIdx + 1 === m.inIdx) {
          // 将[m2.inIdx, m.outIdx]区间的元素往前移动，插入到m2.outIdx之后、m.inIdx之前
          let size = m.outIdx - m2.inIdx + 1;
          let startNo = self.data.boxes[m2.outIdx + 1][m2.boxType + '_no'];
          let items = self.data.boxes.splice(m2.inIdx, size);
          self.data.boxes.splice(m2.outIdx + 1, 0, ...items);
          updateNoAndId(m.boxType, m2.outIdx + 1, m.outIdx, startNo);
          links[key] = links[key2] = null;
          break;
        }
      }
    }
    self.data.boxes.sort(self.cmpBox).forEach((b, i) => b.idx = i);
  }

  function reorderBoxes() {
    function setDeleted(b) {
      ['block', 'column', 'char'].forEach((k) => {
        if ((k + '_no') in b) b[k + '_no'] = null;
        if ((k + '_id') in b) b[k + '_id'] = null;
      });
    }

    let blocks = [], columns = [], chars = [];
    data.boxes.forEach((b) => {
      if (self.isDeleted(b)) return setDeleted(b);
      if (b.boxType === 'char') chars.push(b);
      if (b.boxType === 'block') blocks.push(b);
      if (b.boxType === 'column') columns.push(b);
    });

    self.calcBlockId(blocks);
    self.calcColumnId(columns, blocks);
    self.calcCharId(chars, columns, true, 'down');
    self.data.boxes.sort(self.cmpBox).forEach((b, i) => {
      b.idx = i;
      if (!self.isDeleted(b)) {
        self.removeClass(b, 'odd even');
        let isOdd = b.char_no ? b.column_no % 2 : b.block_no % 2;
        self.addClass(b, isOdd ? 'odd' : 'even');
      }
    });
  }


  function toggleLink(boxType, show) {
    oStatus.curLinkType = boxType;
    $(data.holder).removeClass('show-block-link show-column-link show-char-link');
    if (boxType && show) {
      $(data.holder).addClass('show-' + boxType + '-link');
      drawLink();
    }
  }

  function _traverseLink(start) {
    if (!start.outLink) return [[start.idx, start.cid]];
    else return [[start.idx, start.cid]].concat(_traverseLink(start.outLink.in));
  }

  function _checkLink(boxes) {
    if (!boxes.length) return;
    if (boxes.length === 1) return [[0, boxes[0]['cid']]];

    let start = [], inner = [], end = [], none = [];
    boxes.forEach(function (b) {
      self.removeClass(b, 'highlight ln-error');
      if (b.inLink && b.inLink.elem && b.outLink && b.outLink.elem) inner.push(b);
      else if (b.outLink && b.outLink.elem) start.push(b);
      else if (b.inLink && b.inLink.elem) end.push(b);
      else none.push(b);
    });

    let boxType = boxes[0].boxType;
    let name = {block: '栏框', column: '列框', char: '字框'}[boxType];
    let pName = {block: '页面', column: '栏框', char: '列框'}[boxType];
    if (none.length) {
      bsShow('错误', name + '没有任何连线', 'warning', 2000);
      none.forEach((b) => self.addClass(b, 'highlight ln-error'));
      return false;
    } else if (start.length > 1) {
      bsShow('错误', pName + '内有多个开始' + name, 'warning', 2000);
      start.forEach((b) => self.addClass(b, 'highlight ln-error'));
      return false
    } else if (end.length > 1) {
      bsShow('错误', pName + '内有多个结束' + name, 'warning', 2000);
      end.forEach((b) => self.addClass(b, 'highlight ln-error'));
      return false
    } else if (!start.length) {
      bsShow('错误', '没有找到开始' + name, 'warning', 2000);
      boxes.forEach((b) => self.addClass(b, 'highlight ln-error'));
      return false
    } else if (!end.length) {
      bsShow('错误', '没有找到结束' + name, 'warning', 2000);
      boxes.forEach((b) => self.addClass(b, 'highlight ln-error'));
      return false
    }
    let orders = _traverseLink(start[0]);
    if (orders.length !== boxes.length) {
      bsShow('错误', '连线有中断及环路，不能从开始框依次走到结束框', 'warning', 2000);
      boxes.forEach((b) => self.addClass(b, 'highlight ln-error'));
      return false;
    }
    return orders;
  }

  function checkLinks() {
    // init param
    let blockId2Cid = {}, columnId2Cid = {};
    data.boxes.forEach(function (b) {
      if (b.boxType === 'block') blockId2Cid[b.block_id] = b.cid;
      if (b.boxType === 'column') columnId2Cid[b.column_id] = b.cid
    });
    // classify boxes
    let boxes = {blocks: [], columns: {}, chars: {}};
    data.boxes.forEach(function (b) {
      if (self.isDeleted(b)) return;
      if (b.boxType === 'block') {
        boxes.blocks.push(b);
      } else if (b.boxType === 'column') {
        let blockCid = blockId2Cid['b' + b.block_no];
        boxes.columns[blockCid] = boxes.columns[blockCid] || [];
        boxes.columns[blockCid].push(b);
      } else if (b.boxType === 'char') {
        let colCid = columnId2Cid['b' + b.block_no + 'c' + b.column_no];
        boxes.chars[colCid] = boxes.chars[colCid] || [];
        boxes.chars[colCid].push(b);
      }
    });
    // check blocks
    let links = {blocks: [], columns: {}, chars: {}};
    links.blocks = _checkLink(boxes.blocks);
    if (!links.blocks) return {status: false, errorBoxType: 'block'};
    // check columns
    for (let key in boxes.columns) {
      let order = _checkLink(boxes.columns[key]);
      if (!order) return {status: false, errorBoxType: 'column'};
      links.columns[key] = order;
    }
    // check chars
    for (let key in boxes.chars) {
      let order = _checkLink(boxes.chars[key]);
      if (!order) return {status: false, errorBoxType: 'char'};
      links.chars[key] = order;
    }
    return {status: true, links: links};
  }

  function updateNoByLinks(links) {
    let b = self.getBoxes();
    links.blocks.forEach((c, i) => {
      let b = self.data.boxes[c[0]];
      b['block_no'] = i + 1;
      b['block_id'] = self.getBoxId(b);
    });
    for (let blockCid in links.columns) {
      let _blocks = b.blocks.filter((b) => b.cid == blockCid);
      if (!_blocks.length) continue;
      links.columns[blockCid].forEach((c, i) => {
        let b = self.data.boxes[c[0]];
        b['block_no'] = _blocks[0]['block_no'];
        b['column_no'] = i + 1;
        b['column_id'] = self.getBoxId(b);
      });
    }
    for (let columnCid in links.chars) {
      let _columns = b.columns.filter((b) => b.cid == columnCid);
      if (!_columns.length) continue;
      links.chars[columnCid].forEach((c, i) => {
        let b = self.data.boxes[c[0]];
        b['block_no'] = _columns[0]['block_no'];
        b['column_no'] = _columns[0]['column_no'];
        b['char_no'] = i + 1;
        b['char_id'] = self.getBoxId(b);
      });
    }
    self.data.boxes.sort(self.cmpBox).forEach((b, i) => b.idx = i);
  }

}());
