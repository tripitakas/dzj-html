/**
 * 切分校对工具函数
 * Date: 2020-12-18
 */
(function () {
  'use strict';

  let self = $.box;

  $.extend($.box, {
    calcCharId: calcCharId,
    calcBlockId: calcBlockId,
    calcColumnId: calcColumnId,
    popFields: popFields,
    adjustBoxes: adjustBoxes,
    checkBoxCover: checkBoxCover,
  });

  function pos(elem, which) {
    let a = elem.attrs || elem.elem && elem.elem.attrs, p = {};
    if (a) {
      p = {x: a.x, y: a.y, w: a.width, h: a.height, x2: a.x + a.width, y2: a.y + a.height};
    } else if (elem.x) {
      p = {x: elem.x, y: elem.y, w: elem.w, h: elem.h, x2: elem.x + elem.w, y2: elem.y + elem.h};
    }
    return which ? p[which] : p;
  }

  function checkBoxCover() {
    // 检查框覆盖情况
    let b = self.getBoxes();
    let cover1 = boxesOutOfBoxes(b.chars, b.columns, 0.1);
    if (cover1.outBoxes.length)
      return {status: false, msg: '字框不在列框内', outBoxes: cover1.outBoxes};
    let cover2 = boxesOutOfBoxes(b.columns, b.blocks, 0.2);
    if (cover2.outBoxes.length)
      return {status: false, msg: '列框不在栏框内', outBoxes: cover2.outBoxes};
    // let cover3 = boxesOutOfBoxes(b.chars, b.blocks, 0.2);
    // if (cover3.outBoxes.length)
    //   return {status: false, msg: '字框不在栏框内', outBoxes: cover3.outBoxes};
    return {status: true};
  }

  function adjustBoxes(boxType) {
    // 根据字框调整栏框、列框边界
    let boxes = self.getBoxes();
    (!boxType || boxType === 'blocks') && boxes.blocks.forEach((b) => {
      let p = getOuterRange(boxes.chars.filter((ch) => ch.block_no === b.block_no));
      if (p.x) b.elem.attr({x: p.x, y: p.y, width: p.w, height: p.h});
    });
    (!boxType || boxType === 'columns') && boxes.columns.forEach((b) => {
      let p = getOuterRange(boxes.chars.filter((ch) => ch.block_no === b.block_no && ch.column_no === b.column_no));
      if (p.x) b.elem.attr({x: p.x, y: p.y, width: p.w, height: p.h});
    });
  }

  function popFields(boxes, fields) {
    if (typeof fields === 'string') fields = fields.replace(' ', '').split(',');
    boxes.forEach(function (b) {
      fields.forEach((f) => {
        if (f in b) b[f] = null;
      })
    });
    return boxes;
  }

  function getOuterRange(boxes) {
    let x = 0, y = 0, x2 = 0, y2 = 0;
    boxes.forEach(function (b) {
      let p = pos(b);
      if (!x || p.x < x) x = p.x;
      if (!y || p.y < y) y = p.y;
      if (!x2 || p.x + p.w > x2) x2 = p.x + p.w;
      if (!y2 || p.y + p.h > y2) y2 = p.y + p.h;
    });
    return {x: x, y: y, x2: x2, y2: y2, w: x2 - x, h: y2 - y};
  }

  function lineOverlap(line1, line2, onlyCheck) {
    // 计算两条线段的交叉长度和比例
    let p11 = line1[0], p12 = line1[1], w1 = p12 - p11;
    let p21 = line2[0], p22 = line2[1], w2 = p22 - p21;
    if (p11 > p22 || p21 > p12)
      return onlyCheck ? false : {overlap: 0, r1: 0, r2: 0};
    if (onlyCheck) return true;
    if (!(w1 && w2)) return {overlap: 0, r1: 0, r2: 0};
    let overlap = w1 + w2 - (Math.max(p12, p22) - Math.min(p11, p21));
    let ratio1 = Math.round(overlap * 100 / w1) / 100;
    let ratio2 = Math.round(overlap * 100 / w2) / 100;
    return {overlap: overlap, r1: ratio1, r2: ratio2};
  }

  function boxOverlap(box1, box2, onlyCheck) {
    // 计算两个框的交叉面积和比例。如果onlyCheck为True，则只要交叉就返回True
    let b1 = pos(box1), b2 = pos(box2);
    let x1 = b1.x, y1 = b1.y, w1 = b1.w, h1 = b1.h;
    let x2 = b2.x, y2 = b2.y, w2 = b2.w, h2 = b2.h;
    if (x1 > x2 + w2 || x2 > x1 + w1 || y1 > y2 + h2 || y2 > y1 + h1)
      return onlyCheck ? false : {overlap: 0, r1: 0, r2: 0};
    if (onlyCheck) return true;
    if (!(w1 && w2 && h1 && h2)) return {overlap: 0, r1: 0, r2: 0};
    let col = Math.abs(Math.min(x1 + w1, x2 + w2) - Math.max(x1, x2));
    let row = Math.abs(Math.min(y1 + h1, y2 + h2) - Math.max(y1, y2));
    let overlap = col * row;
    let ratio1 = Math.round(overlap * 100 / (w1 * h1)) / 100;
    let ratio2 = Math.round(overlap * 100 / (w2 * h2)) / 100;
    return {overlap: overlap, r1: ratio1, r2: ratio2};

  }

  function getBoxOverlap(box1, box2, direction) {
    if (!direction)
      return boxOverlap(box1, box2);
    let b1 = pos(box1), b2 = pos(box2);
    if (direction === 'x')
      return lineOverlap([b1.x, b1.x2], [b2.x, b2.x2]);
    if (direction === 'y')
      return lineOverlap([b1.y, b1.y2], [b2.y, b2.y2]);
  }

  function getBoxesOfRegion(boxes, region, ratio, setRatio) {
    // 筛选某范围内的框，当box和region重叠的面积占box面积的比例大于ratio时入选
    return boxes.filter(function (b) {
      if (self.isDeleted(b)) return;
      let r1 = boxOverlap(b, region).r1;
      if (r1 > ratio) {
        if (setRatio) b['ratio'] = r1;
        return true;
      }
    });
  }

  function boxesOutOfBoxes(boxes1, boxes2, ratio, onlyCheck) {
    // ratio指的是box1和box2重叠的面积占box1的比例最小值
    let outBoxes = [], inBoxes = [];
    for (let i = 0, len1 = boxes1.length; i < len1; i++) {
      let b1 = boxes1[i];
      if (self.isDeleted(b1)) return;
      let isIn = false;
      for (let j = 0, len2 = boxes2.length; j < len2; j++) {
        let r1 = boxOverlap(b1, boxes2[j]).r1;
        if (r1 > ratio) {
          isIn = true;
          break;
        }
      }
      if (!isIn) {
        outBoxes.push(b1);
        if (onlyCheck) return true;
      } else {
        inBoxes.push(b1);
      }
    }
    return onlyCheck ? false : {outBoxes: outBoxes, inBoxes: inBoxes};
  }

  function cmpUp2Down(a, b) {
    // 先整体从上到下，次局部从右到左
    let rx = getBoxOverlap(a, b, 'x');
    let ry = getBoxOverlap(a, b, 'y');
    // 当二者在y轴上交叉且x轴几乎不交叉时，认为二者是水平邻居，则从右到左，即x值大的在前
    if ((ry.r1 > 0.5 || ry.r2 > 0.5) && (ry.r1 > 0.25 || ry.r2 > 0.25) && (rx.r1 < 0.25 && rx.r2 < 0.25))
      return pos(b).x - pos(a).x;
    // 否则，从上到下，即y值小的在前
    else
      return pos(a).y - pos(b).y;
  }

  function cmpRight2Left(a, b) {
    // 先整体从右到左，次局部从上到下
    let rx = getBoxOverlap(a, b, 'x');
    let ry = getBoxOverlap(a, b, 'y');
    // # 当二者在x轴上交叉且y轴几乎不交叉时，认为二者是上下邻居，则从上到下，即y值小的在前
    if ((rx.r1 > 0.5 || rx.r2 > 0.5) && (rx.r1 > 0.25 && rx.r2 > 0.25) && (ry.r1 < 0.25 && ry.r2 < 0.25))
      return pos(a).y - pos(b).y;
    // # 否则，从右到左，即x值大的在前
    else
      return pos(b).x - pos(a).x;
  }

  function calcBlockId(blocks) {
    // 计算并设置栏序号，包括block_no/block_id
    popFields(blocks, ['block_no', 'block_id']);
    blocks.sort(cmpUp2Down);
    blocks.forEach(function (b, i) {
      b['block_no'] = i + 1;
      b['block_id'] = 'b' + b['block_no'];
    });
    return blocks;
  }

  function calcColumnId(columns, blocks) {
    // 计算和设置列序号，包括column_no/column_id。假定blocks已排好序
    popFields(columns, ['block_no', 'column_no', 'column_id']);
    // 设置栏号
    columns.forEach(function (c) {
      let inBlock = null, r = 0;
      blocks.forEach((b) => {
        let r1 = boxOverlap(c, b).r1;
        if (r1 > r) {
          inBlock = b;
          r = r1;
        }
      });
      if (inBlock) c['block_no'] = inBlock['block_no'];
    });
    // 按栏分列
    let inColumns = [];
    blocks.forEach((b) => {
      let bColumns = columns.filter((c) => c['block_no'] === b['block_no']);
      bColumns.sort(cmpRight2Left).forEach((c, i) => {
        c['column_no'] = i + 1;
        c['column_id'] = 'b' + c['block_no'] + 'c' + c['column_no'];
      });
      inColumns.concat(bColumns);
    });
    // 栏外的列
    let outColumns = columns.filter((c) => !c['block_no']);
    outColumns.forEach((c, i) => {
      c['block_no'] = 0;
      c['column_no'] = i + 1;
      c['column_id'] = 'b' + c['block_no'] + 'c' + c['column_no'];
    });
    // 设置返回
    return outColumns.concat(inColumns)
  }

  /**
   * 针对字框排序，并设置char_no/char_id等序号
   *:param chars: list, 待排序的字框
   *:param columns: list, 字框所在的列，假定已排序并设置序号
   *:param detectCol: bool, 当字框属于多列时，是否自适应的检测和调整
   *:param smallDirection: str, 下一个夹注小字的方向，down表示往下找，left表示往左找
   */
  function calcCharId(chars, columns, detectCol, smallDirection) {
    let columnDict = {}, columnsChars = {};
    let nmChW = 0, nmChH = 0, nmChA = 0, nmClW = 0;

    function initParams() {
      // 计算正常字框的宽度、高度和面积
      let ch = chars.map((c) => pos(c, 'w')).sort((a, b) => b - a), len = ch.length;
      let bigCh = len > 3 ? ch[2] : len > 2 ? ch[1] : ch[0];
      let size = 0, chWs = 0, chHs = 0, chAs = 0;
      chars.forEach((c) => {
        let cp = pos(c);
        if (bigCh * 0.75 < cp.w <= bigCh) {
          ++size;
          chWs += cp.w;
          chHs += cp.h;
          chAs += cp.w * cp.h;
        }
      });
      nmChW = chWs / size;
      nmChH = chHs / size;
      nmChA = chAs / size;
      // 计算正常列框的宽度
      let cl = columns.map((c) => pos(c, 'w')).sort((a, b) => b - a), len2 = cl.length;
      let bigCl = len2 > 3 ? cl[2] : len2 > 2 ? cl[1] : cl[0];
      let size2 = 0, clWs = 0;
      columns.forEach((c) => {
        let cp = pos(c);
        if (bigCl * 0.75 < cp.w <= bigCl) {
          ++size2;
          clWs += cp.w;
        }
      });
      nmClW = clWs / size2;
    }

    function cmpSmall(a, b) {
      let side2int = {left: 3, center: 2, right: 1};
      if (a['side'] !== b['side'])
        return side2int[a['side']] - side2int[b['side']];
      else
        return pos(a).y - pos(b).y;
    }

    function isNarrowColumn(colId) {
      return pos(columnDict[colId]).w <= nmClW * 0.6;
    }

    function isHrNeighbor(a, b) {
      let rx = getBoxOverlap(a, b, 'x');
      let ry = getBoxOverlap(a, b, 'y');
      // # 二者在y轴有交叉，x轴交叉不大，则认为是水平邻居
      return (ry.r1 > 0.25 || ry.r2 > 0.25) && (rx.r1 < 0.25 && rx.r2 < 0.25);
    }

    // 计算字框的位置和列宽的占比
    function getSideAndRatio(ch, colChars, colRange) {
      let cp = pos(ch);
      let nbChars = colChars.filter((c) => c['hr_nbs'].length).map((c) => [c, Math.abs(pos(c).y - cp.y)]);
      let outRange = colRange; // 以整列的外包络作为参照
      if (nbChars) { // 以最近的并排夹注小字的作为参照
        let nbCh = nbChars.sort((a, b) => a[1] - b[1])[0][0];
        outRange = getOuterRange(nbCh['hr_nbs'].concat([nbCh]));
      }
      let rW = lineOverlap([outRange['x'], outRange['x'] + outRange['w']], [cp['x'], cp['x'] + cp['w']])[1];
      let cenLine = outRange['x'] + outRange['w'] * 0.5;
      ch['side'] = cp['x'] + cp['w'] * 0.5 < cenLine ? 'left' : 'right';
      let cenInterval = [outRange['x'] + outRange['w'] * 0.25, outRange['x'] + outRange['w'] * 0.75];
      let r = lineOverlap(cenInterval, [cp['x'], cp['x'] + cp['w']]);
      if (r.r2 > 0.99 || r.r1 > 0.99 || (r.r1 > 0.8 && r.r1 + r.r2 > 1.6))
        ch['side'] = 'center';
      return [ch['side'], rW];
    }

    function setColumnId() {
      // 1.初步设置column_id和size参数
      chars.forEach((c) => {
        let cp = pos(c);
        let r = cp.w / nmChW, a = (cp.w * cp.h) / nmChA;
        c['size'] = (r > 0.85 && a > 0.65) ? 'big' : (r < 0.55 && a < 0.35) ? 'small' : 'median';
        let inColumns = columns.filter((col) => boxOverlap(c, col).r1 > 0.25);
        if (!inColumns.length)
          c['column_id'] = 'b0c0';
        else if (inColumns.length === 1)
          c['column_id'] = inColumns[0]['column_id'];
        else { // 字框在多列时，根据字框面积主要落在哪列设置column_id
          inColumns = inColumns.map((col) => [boxOverlap(c, col).r1, col]).sort((a, b) => b[0] - a[0]);
          c['column_id'] = inColumns[0][1]['column_id'];
          c['column_id2'] = inColumns[1][1]['column_id'];
        }
      });
      // 2.进一步调整字框落在多列的情况
      detectCol && chars.forEach((c) => {
        if (c['column_id2'] && !isNarrowColumn(c['column_id']) && c['size'] !== 'big') {
          // 如果有上邻居，就随上邻居
          let cp = pos(c);
          let region = {x: cp['x'], y: cp['y'] - nmChH, w: cp['w'], h: nmChH};
          let upNbs = getBoxesOfRegion(chars, region, 0.1, true);
          if (upNbs.length) {
            upNbs.sort((a, b) => b.ratio - a.ratio);
            c['column_id'] = upNbs[0]['column_id'];
            return popFields(upNbs, 'ratio');
          }
          // 没有上邻居，就检查两列的水平邻居
          let column1 = pos(columnDict[c['column_id']]), column2 = pos(columnDict[c['column_id2']]);
          let x = Math.min(column1['x'], column2['x']);
          let w = Math.max(column1['x'] + column1['w'], column2['x'] + column2['w']) - x;
          let hrNbs = getBoxesOfRegion(chars, {x: x, y: cp['y'], w: w, h: cp['h']}, 0.1);
          let hrNbs1 = hrNbs.filter((n) => n['column_id'] = c['column_id']);
          let hrNbs2 = hrNbs.filter((n) => n['column_id'] = c['column_id2']);
          // 比较把c放过去之后两列的水平宽度
          let hrW1 = getOuterRange(hrNbs1)['w'];
          let hrW2 = getOuterRange(hrNbs2.concat([c]))['w'];
          if (hrW1 < hrW2) c['column_id'] = c['column_id2'];
        }
      });
      // 3.根据column_id分组
      chars.forEach((c) => {
        let colId = c['column_id'];
        columnsChars[colId] = columnsChars[colId] || [];
        columnsChars[colId].push(c);
      });
    }

    function scanAndOrder(columnId, columnChars) {
      // 检查是否为b0c0
      if (columnId === 'b0c0') {
        columnChars.sort(cmpUp2Down).forEach((c, i) => c['char_no'] = i + 1);
        return columnChars;
      }
      // 初步检查、设置字框的水平邻居
      let colLen = columnChars.length;
      columnChars.forEach((c, i) => {
        c['hr_nbs'] = c['hr_nbs'] || [];
        for (let j = 1; j < 5 && i + j < colLen; j++) {  // 往后找4个节点
          let n = columnChars[i + j];
          if (isHrNeighbor(c, n)) {
            n['hr_nbs'] = n['hr_nbs'] || [];
            n['hr_nbs'].push(c);
            c['hr_nbs'].push(n);
          }
        }
      });
      // 进一步检查水平邻居中的上下关系
      columnChars.forEach((c, i) => {
        let hrNbs = c['hr_nbs'];
        if (!hrNbs || hrNbs.length < 2) return;
        let resNbs = [], handled = [];
        hrNbs.forEach((b) => {
          if (handled.indexOf(b.cid) < 0) {
            // 从所有水平邻居中找出和b有上下关系的节点
            let dupNbs = hrNbs.filter((n) => getBoxOverlap(b, n).r1 > 0.25);
            // 从上下关系的节点中选择和c在y轴上重复度最大的节点
            let nb = dupNbs.map((n) => [getBoxOverlap(c, n).r1, n]).sort((a, b) => b[0] - a[0])[0];
            resNbs.push(nb[1]);
            handled.concat(dupNbs.map((n) => n.cid));
          }
        });
        c['hr_nbs'] = resNbs;
      });
      // 检查最多的水平邻居数，以此判断是否有小字以及小字的列数
      let maxNbCnt = Math.max(...columnChars.map((c) => (c['hr_nbs'] || []).length));
      if (maxNbCnt === 0) { // 整列无水平邻居，则直接排序、返回
        columnChars.sort(cmpUp2Down).forEach((c, i) => c['char_no'] = i + 1);
        return columnChars;
      }
      // 检查、设置是否夹注小字
      let colRange = getOuterRange(columnChars);
      columnChars.forEach((c) => {
        if (c['hr_nbs'].length)
          c['is_small'] = true;
        else if (c['size'] === 'big')
          c['is_small'] = false;
        else {
          let cp = pos(c);
          let r = getSideAndRatio(c, columnChars, colRange);
          let side = r[0], rW = r[1]; // rW为字宽占附近列宽的比例
          if (side === 'center') {
            if (rW > 0.6 || c['size'] === 'median')
              c['is_small'] = false;
            else { // 居中小字
              c['is_small'] = true;
              // 如果下邻居也无左右邻居且大小和位置跟自己差不多，则是连续的非夹注小字
              let dnRegion = {x: cp['x'], y: cp['y'] + cp['h'], w: cp['w'], h: nmChH};
              let dnNbs = getBoxesOfRegion(columnChars, dnRegion, 0.25);
              if (dnNbs.length) {
                let dnb = dnNbs.sort((a, b) => pos(a).y - pos(b).y)[0];
                r = getSideAndRatio(dnb, columnChars, colRange);
                if (!dnb['hr_nbs'].length && r[0] === 'center' && r[1] < 0.6)
                  c['is_small'] = false;
              }
            }
          } else {
            if (rW > 0.75)
              c['is_small'] = false;
            else if (rW < 0.5)
              c['is_small'] = true;
            else { // 不居中的中号字
              c['is_small'] = true;
              let upRegion = {x: cp['x'], y: cp['y'] - nmChH, w: cp['w'], h: nmChH};
              let upNbs = getBoxesOfRegion(columnChars, upRegion, 0.25);
              if (upNbs.length) {
                let dnb = upNbs.sort((a, b) => pos(b).y - pos(a).y)[0];
                c['is_small'] = dnb['is_small'];
              }
            }
          }
        }
      });
      // 检查、设置左右位置，以便排序
      columnChars.forEach((c) => {
        if (c['is_small'] && !c['side'])
          getSideAndRatio(c, columnChars, colRange);
      });
      // 针对连续的夹注小字重新排序
      let smallStart = null, len = columnChars.length;
      columnChars.forEach((c, i) => {
        if (c['is_small']) {
          if (!smallStart) smallStart = i;
          let next = i + 1 < len ? columnChars[i + 1] : null;
          if (!next || !next['is_small']) {
            let sliceChars = columnChars.slice(smallStart, i + 1);
            sliceChars.sort((maxNbCnt === 1 && i - smallStart >= 5) ? cmpSmall : cmpRight2Left);
            columnChars.splice(smallStart, i + 1 - smallStart, ...sliceChars);
            smallStart = null;
          }
        }
      });
      return columnChars;
    }

    function setSubColumns(columnId, columnChars) {
      let sub = {columns: [], col: [], no: 1, isNew: false};
      columnChars.forEach((c, i) => {
        if (!sub.col.length) return sub.col.push(c);
        let lst = sub.col[sub.col.length - 1];
        let cp = pos(c), lp = pos(lst);
        if (c['is_small'])
          sub.isNew = !lst['is_small'] || (cp['y'] < lp['y'] + lp['h'] / 2);
        else if (lst['is_small'])
          sub.isNew = true;
        if (sub.isNew) {
          let p = getOuterRange(sub.col);
          sub.columns.push({x: p.x, y: p.y, w: p.w, h: p.h, 'sub_no': sub.no, 'column_id': columnId + '#' + sub.no});
          Object.assign(sub, {col: [c], no: sub.no + 1, isNew: false});
        } else {
          sub.columns.push(c);
        }
      });
      if (sub.col.length) {
        let p = getOuterRange(sub.col);
        sub.columns.push({x: p.x, y: p.y, w: p.w, h: p.h, 'sub_no': sub.no, 'column_id': columnId + '#' + sub.no});
      }
      if (columnId !== 'b0c0' && sub.columns.length > 1)
        columnDict[columnId]['sub_columns'] = sub.columns;
    }

    if (!chars || !chars.length) return;
    popFields(chars, 'column_id,column_id2,char_no,hr_nbs,side');
    smallDirection = smallDirection || 'down';

    let retChars = [];
    columns.forEach((c) => columnDict[c['column_id']] = c);
    initParams();
    setColumnId();
    for (let columnId in columnsChars) {
      let columnChars = columnsChars[columnId];
      columnChars.sort(cmpUp2Down);
      if (smallDirection === 'down') {
        columnChars = scanAndOrder(columnId, columnChars);
        setSubColumns(columnId, columnChars);
      }
      columnChars.forEach((c, i) => {
        let a = columnId.substr(1).split('c');
        Object.assign(c, {
          'char_no': i + 1, 'block_no': parseInt(a[0]), 'column_no': parseInt(a[1]),
          'char_id': columnId + 'c' + (i + 1)
        });
        retChars.push(c);
      });
    }
    retChars.sort((a, b) => {
      if (a.block_no !== b.block_no) return a.block_no > b.block_no;
      if (a.column_no !== b.column_no) return a.column_no > b.column_no;
      if (a.char_no !== b.char_no) return a.char_no > b.char_no;
    });
    popFields(retChars, 'column_id,column_id2,hr_nbs,side,ratio');
    return retChars;
  }

}());
