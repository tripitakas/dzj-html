/**
 * 切分校对
 * 1. 用户对字框的修改记录在box.op属性中，该属性可能为空，或者added/deleted/changed/recovered。
 *    - added 用户此次新增的字框
 *    - deleted 用户此次删除的字框。注：如果删除的是此次新增的字框，则直接删除，不需记录
 *    - changed 用户此次修改的字框。注：如果是用户新增的字框，则修改时其op属性仍为added
 *    - recovered 用户恢复自己曾经删除的字框。注：如果恢复此次删除的字框，则直接取消deleted设置即可
 * 2. 字框修改事件通过self.notifyChanged传递给回调函数
 * Date: 2020-11-21
 */
(function () {
  'use strict';

  $.box.onBoxChanged(function (box, reason, param) {
    if (reason === 'switch') {
      switchCurHandles(box);
    }
    if (reason === 'zoom') {
      switchCurHandles($.box.status.curBox);
    }
  });

  let self = $.box;
  let data = self.data;
  let status = self.status;
  let cStatus = {
    onlyChange: false,                              // 是否仅允许修改
    hasChanged: false,                              // 用户是否已修改
    isMouseDown: false,                             // 鼠标左键是否按下
    isDragging: false,                              // 鼠标是否在点击拖拽
    dragMode: null,                                 // 鼠标拖拽模式，1表示修改，2表示新增
    dragHandleIndex: -1,                            // 鼠标拖拽哪个控制点
    isMulti: false,                                 // 是否为多选模式
    downPt: null,                                   // 点击的坐标
    curHandles: [],                                 // 当前box的控制点
    sensitiveGap: 8,                                // 控制点的敏感距离
    dragPt: null,                                   // 当前拖拽的坐标
    dragElem: null,                                 // 当前拖拽box的Raphael元素
    hoverElem: null,                                // 掠过box的Raphael元素
    step: {lastTime: 0, unit: 1},                   // 快捷键操作时的微调量
  };

  $.extend($.box, {
    cStatus: cStatus,
    initCut: initCut,
    moveBox: moveBox,
    copyBox: copyBox,
    isCutMode: isCutMode,
    resizeBox: resizeBox,
    deleteBox: deleteBox,
    changeBox: changeBox,
    recoverBox: recoverBox,
    checkBoxes: checkBoxes,
    deleteBoxes: deleteBoxes,
    unChangeBox: unChangeBox,
    toggleMulti: toggleMulti,
    deleteBoxByIdxes: deleteBoxByIdxes,
    exportSubmitData: exportSubmitData,
    selectBoxesByShape: selectBoxesByShape,
  });

  function isCutMode() {
    return status.boxMode === 'cut';
  }

  function initCut(p) {
    if (p && p.onlyChange) cStatus.onlyChange = true;
    $(data.holder).find('svg').on('dblclick', dblclick).mousedown(mouseDown).mouseup(mouseUp).mousemove(function (e) {
      if (!cStatus.isMouseDown) mouseHover(e);
      else if (self.getDistance(self.getPoint(e), cStatus.downPt) > data.ratio) //仅当拖拽距离大于1时才触发拖拽函数
        mouseDrag(e);
    });
  }

  function dblclick(e) {
    if (!isCutMode() || !$(data.holder).hasClass('usr-hint')) return;
    e.preventDefault();
    let pt = self.getPoint(e);
    let box = findHintBoxByPoint(pt, status.curBoxType);
    if (box && self.hasClass(box.hint.elem, 'h-deleted')) {
      recoverBox(box);
      box.hint && box.hint.elem && box.hint.elem.remove();
      box.hint = {};
    }
  }

  function mouseDown(e) {
    if (!isCutMode() || !status.curBoxType) return;
    e.preventDefault();

    if (e.button === 2) return; // 鼠标右键
    cStatus.isDragging = false;
    cStatus.isMouseDown = true;
    cStatus.downPt = self.getPoint(e);
  }

  function mouseDrag(e) {
    if (!isCutMode() || !status.curBoxType || status.readonly) return;
    e.preventDefault();

    let pt = self.getPoint(e);
    cStatus.dragPt = pt;
    cStatus.isDragging = true;
    cStatus.dragElem && cStatus.dragElem.remove();
    if (!cStatus.dragMode) {
      cStatus.dragMode = (status.curBox && self.isInRect(pt, status.curBox, 5)) ? 1 : 2;
      cStatus.dragHandleIndex = setActiveHandle(pt);
    }
    if (cStatus.dragMode === 1) { // 1.修改字框
      cStatus.dragElem = dragHandle(cStatus.dragPt);
      self.addClass(status.curBox, 'on-drag');
    } else { // 2.新增字框
      if (cStatus.onlyChange) return;
      cStatus.dragElem = self.createRect(cStatus.downPt, cStatus.dragPt,
          'box dragging ' + status.curBoxType, true);
    }
    switchCurHandles(cStatus.dragElem, true);
  }

  function mouseUp(e) {
    if (!isCutMode() || !status.curBoxType) return;
    e.preventDefault();

    let pt = self.getPoint(e);
    if (cStatus.isDragging) { // 1.拖拽弹起
      cStatus.dragPt = self.getPoint(e);
      if (cStatus.dragMode === 1) { // 1.1.修改字框
        self.removeClass(status.curBox, 'on-drag');
        if (self.getDistance(cStatus.downPt, cStatus.dragPt) > data.ratio) { // 1.1.1.应用修改
          cStatus.dragElem && updateBox(status.curBox, cStatus.dragElem);
        } else { // 1.1.2.放弃很小的移动
          cStatus.dragElem && cStatus.dragElem.remove();
          self.switchCurBox(status.curBox);
          setActiveHandle(pt);
        }
      } else { // 1.2.新增字框
        if (cStatus.isMulti) selectBoxes(cStatus.dragElem, e.shiftKey);
        else addBox(cStatus.dragElem);
      }
    } else { // 2.点击弹起
      cStatus.downPt = pt;
      let box = self.findBoxByPoint(pt, status.curBoxType, canHit);
      if (cStatus.isMulti) { // 2.1.多选模式，设置选中
        box && self.toggleClass(box, 'u-selected');
      } else { // 2.2.单选模式，设置当前字框
        cStatus.dragElem && cStatus.dragElem.remove();
        self.switchCurBox(box);
        setActiveHandle(pt);
      }
    }
    cStatus.dragMode = null;
    cStatus.dragElem = null;
    cStatus.isDragging = false;
    cStatus.isMouseDown = false;
  }

  function mouseHover(e) {
    if (!isCutMode() || !status.curBoxType || status.readonly) return;
    e.preventDefault();

    let pt = self.getPoint(e);
    let box = self.findBoxByPoint(pt, status.curBoxType, canHit);
    if (box && (!cStatus.hoverElem || (cStatus.hoverElem.id !== box.elem.id))) {
      self.removeClass(cStatus.hoverElem, 'hover');
      self.addClass(box, 'hover');
      cStatus.hoverElem = box.elem;
    }
    if (!box) self.removeClass(cStatus.hoverElem, 'hover');
    if (status.curBox) setActiveHandle(pt);
  }

  function toggleMulti(multi) {
    multi = multi || !cStatus.isMulti;
    cStatus.isMulti = !!multi;
    if (cStatus.isMulti) {
      $(data.holder).addClass('multi');
      if (status.curBox) {
        self.addClass(status.curBox, 'u-selected');
        self.switchCurBox(null);
      }
    } else {
      data.boxes.forEach(function (box) {
        if (self.hasClass(box, 'u-selected')) self.removeClass(box, 'u-selected');
      });
      $(data.holder).removeClass('multi');
    }

  }

  function addBox(boxElem, boxType) {
    if (!boxElem) return;
    boxType = boxType || status.curBoxType;
    if (!boxType || boxType === 'all') {
      boxElem.remove();
      return bsShow('错误', `请选择${boxType ? '仅' : ''}一种切分框类型`, 'warning', 2000);
    }
    let box = {
      boxType: boxType, idx: data.boxes.length, cid: self.getMaxCid(boxType) + 1,
      elem: boxElem, op: 'added',
    };
    self.removeClass(boxElem, 'dragging');
    self.addClass(box, boxType + ' u-added');
    data.boxes.push(box);
    self.switchCurBox(box);
    cStatus.hasChanged = true;
    self.notifyChanged(box, 'added');
    return box;
  }

  function copyBox() {
    if (status.curBox) {
      let box = addBox(status.curBox.elem.clone(), status.curBox.boxType);
      _moveBox(box, 'right', 10);
      _moveBox(box, 'down', 10);
      self.switchCurBox(box);
      return box;
    }
  }

  function updateBox(curBox, dragElem) {
    let e = curBox.elem.attrs, p = dragElem.attrs;
    let oldPos = {x: e.x, y: e.y, width: e.width, height: e.height};
    let newPos = {x: p.x, y: p.y, width: p.width, height: p.height};
    curBox.elem.attr(newPos);
    dragElem.remove();
    if (!curBox.op) curBox.op = 'changed';
    self.addClass(curBox, 'u-changed');
    self.switchCurBox(curBox);
    cStatus.hasChanged = true;
    self.notifyChanged(curBox, 'changed', {type: 'change', old_pos: oldPos, new_pos: newPos});
  }

  function _deleteBox(box) {
    if (cStatus.onlyChange) return;
    if (box.op === 'added') { // 直接删除此次新增的字框
      self.addClass(box, 's-deleted');  // 标记为系统删除，将不会传给后台
    } else { // 标记删除此前新增的字框
      self.addClass(box, 'u-deleted'); // 标记为用户删除
    }
    self.removeClass(box, 'hover highlight');
    box.op = 'deleted';
    cStatus.hasChanged = true;
    return box;
  }

  function deleteBox(box, unNotify) {
    if (box) {
      _deleteBox(box);
      if (self.hasClass(box, 'current')) self.navigate('down');
      !unNotify && self.notifyChanged(box, 'deleted');
      return;
    }
    if (cStatus.isMulti) {
      if (self.hasClass(status.curBox, 'u-selected')) self.switchCurBox(null);
      let boxes = [];
      data.boxes.forEach(function (box) {
        if (self.hasClass(box, 'u-selected')) boxes.push(_deleteBox(box));
      });
      !unNotify && self.notifyChanged(boxes, 'deleted');
    } else if (status.curBox) {
      _deleteBox(status.curBox);
      !unNotify && self.notifyChanged(status.curBox, 'deleted');
      self.navigate('down');
    }
  }

  function deleteBoxes(boxType, cids, unNotify) {
    let boxes = [];
    data.boxes.forEach(function (box) {
      if ((box.boxType === boxType) && (!cids || cids.indexOf(box.cid) > -1)) {
        boxes.push(_deleteBox(box));
      }
    });
    !unNotify && self.notifyChanged(boxes, 'deleted');
  }

  function deleteBoxByIdxes(boxIdxes) {
    let boxes = [];
    boxIdxes.forEach(function (idx) {
      boxes.push(_deleteBox(data.boxes[idx]));
    });
    self.notifyChanged(boxes, 'deleted');
    bsHide();
  }

  function recoverBox(box, unNotify) {
    box.op = box.op === 'deleted' ? '' : 'recovered';
    self.removeClass(box, 's-deleted u-deleted b-deleted');
    cStatus.hasChanged = true;
    !unNotify && self.notifyChanged(box, 'recovered');
  }

  function selectBoxes(rangeElem, reverse) {
    if (!cStatus.isMulti || !rangeElem) return;
    data.boxes.forEach(function (box) {
      if (canHit(box) && self.isOverlap(box.elem, rangeElem)) {
        reverse ? self.removeClass(box, 'u-selected') : self.addClass(box, 'u-selected');
      }
    });
    rangeElem.remove();
  }

  function selectBoxesByShape(shape, reverse) {
    if (!cStatus.isMulti) return;
    if ('white/opacity'.indexOf(shape) > -1) return;
    if (status.curBoxType !== 'char' && shape !== 'overlap') return;
    data.boxes.forEach((box) => {
      if (canHit(box) && self.hasClass(box.elem, 's-' + shape)) {
        reverse ? self.removeClass(box, 'u-selected') : self.addClass(box, 'u-selected');
      }
    });
  }

  function getUnit(unit) {
    if (!unit) {
      // unit随时间改变：慢速启动，加速移动
      let now = new Date().getTime();
      cStatus.step.unit = (cStatus.step.lastTime && ((now - cStatus.step.lastTime) < 200)) ? cStatus.step.unit + 3 : 1;
      cStatus.step.lastTime = now;
      unit = cStatus.step.unit;
    }
    return unit
  }

  function _moveBox(box, direction, unit) {
    let p = box.elem.attrs;
    if (direction === 'left') box.elem.attr({'x': p.x - unit});
    if (direction === 'right') box.elem.attr({'x': p.x + unit});
    if (direction === 'up') box.elem.attr({'y': p.y - unit});
    if (direction === 'down') box.elem.attr({'y': p.y + unit});
    if (!box.op) box.op = 'changed';
    self.addClass(box, 'u-changed');
    cStatus.hasChanged = true;
    return box;
  }

  function moveBox(direction, unit) {
    unit = getUnit(unit);
    let boxType = status.curBoxType;
    let param = {type: 'move', direction: direction, unit: unit};
    if (cStatus.isMulti) {
      let boxes = [];
      data.boxes.forEach(function (box) {
        if (self.hasClass(box, 'u-selected') && (boxType === 'all' || box.boxType === boxType))
          boxes.push(_moveBox(box, direction, unit));
      });
      if (self.hasClass(status.curBox, 'u-selected')) self.switchCurBox(status.curBox);
      self.notifyChanged(boxes, 'changed', param);
    } else if (status.curBox) {
      _moveBox(status.curBox, direction, unit);
      self.switchCurBox(status.curBox);
      self.notifyChanged(status.curBox, 'changed', param);
    }
  }

  function _resizeBox(box, direction, unit) {
    let p = box.elem.attrs;
    if (direction === 'left') box.elem.attr({'width': p.width + unit, 'x': p.x - unit});
    if (direction === 'right') box.elem.attr({'width': p.width + unit});
    if (direction === 'up') box.elem.attr({'height': p.height + unit, 'y': p.y - unit});
    if (direction === 'down') box.elem.attr({'height': p.height + unit});
    if (!box.op) box.op = 'changed';
    self.addClass(box, 'u-changed');
    cStatus.hasChanged = true;
    return box;
  }

  function resizeBox(direction, zoom) {
    let unit = getUnit();
    let boxType = status.curBoxType;
    unit = zoom ? unit : -unit;
    let param = {type: 'resize', direction: direction, unit: unit};
    if (cStatus.isMulti) {
      let boxes = [];
      data.boxes.forEach(function (box) {
        if (self.hasClass(box, 'u-selected') && (boxType === 'all' || box.boxType === boxType))
          boxes.push(_resizeBox(box, direction, unit));
      });
      if (self.hasClass(status.curBox, 'u-selected')) self.switchCurBox(status.curBox);
      self.notifyChanged(boxes, 'changed', param);
    } else if (status.curBox) {
      _resizeBox(status.curBox, direction, unit);
      self.switchCurBox(status.curBox);
      self.notifyChanged(status.curBox, 'changed', param);
    }
  }

  function unChangeBox(box, param) {
    if (param.type === 'resize') {
      param.direction && _resizeBox(box, param.direction, -param.unit)
    }
    if (param.type === 'move') {
      param.direction && _moveBox(box, param.direction, -param.unit)
    }
    if (param.type === 'change') {
      let p = param['old_pos'];
      p && box.elem.attr({x: p.x, y: p.y, width: p.width, height: p.height});
      self.switchCurBox(box);
    }
  }

  function changeBox(box, param) {
    if (param.type === 'resize') {
      param.direction && _resizeBox(box, param.direction, param.unit)
    }
    if (param.type === 'move') {
      param.direction && _moveBox(box, param.direction, param.unit)
    }
    if (param.type === 'change') {
      let p = param['new_pos'];
      p && box.elem.attr({x: p.x, y: p.y, width: p.width, height: p.height});
      self.switchCurBox(box);
    }
  }

  function canHit(box) {
    if (!box || !box.elem || !box.elem.attrs) return false;
    if (status.curBoxType !== 'all' && status.curBoxType !== box.boxType) return false;
    return !self.hasClass(box, 'hide')
        && !self.hasClass(box, 'hint')
        && !self.hasClass(box, 's-deleted')
        && !self.hasClass(box, 'u-deleted')
        && !self.hasClass(box, 'b-deleted')
  }

  function findHintBoxByPoint(pt, boxType) {
    let ext = 5; // 字框四边往外延伸的冗余量
    let ret = null, dist = 1e5;
    data.boxes.forEach(function (box) {
      let elem = box.hint && box.hint.elem;
      if (elem && (boxType === 'all' || box.boxType === boxType) && self.isInRect(pt, elem, ext)) {
        for (let j = 0; j < 8; j++) {
          let d = self.getDistance(pt, self.getHandlePt(elem, j));
          if (d < dist) {
            dist = d;
            ret = box;
          }
        }
      }
    });
    return ret;
  }

  function dragHandle(pt) {
    let index = cStatus.dragHandleIndex;
    if (index === -1) return;
    let pt1 = pt, b = status.curBox.elem.getBBox();
    // 4<=index<8，拖动四条边
    if (index === 4) pt1.x = b.x;
    if (index === 5) pt1.y = b.y;
    if (index === 6) pt1.x = b.x + b.width;
    if (index === 7) pt1.y = b.y + b.height;
    let pt2 = self.getHandlePt(status.curBox.elem, (index + 2) % 4);
    return self.createRect(pt1, pt2, 'box dragging ' + status.curBoxType, true);
  }

  function setActiveHandle(pt) {
    let index = -1, gap = -1;
    if (!status.curBox) return index;
    if (pt && self.isInRect(pt, status.curBox, cStatus.sensitiveGap)) {
      cStatus.curHandles.forEach(function (h, i) {
        self.removeClass(h, 'active');
        let d = self.getDistance(pt, h.getBBox());
        if (gap === -1 || d < gap) {
          index = i;
          gap = d;
        }
      });
    }
    if (index > -1) self.addClass(cStatus.curHandles[index], 'active');
    return index;
  }

  function switchCurHandles(box, force) {
    if ($.box.status.readonly) return;
    // 清空curHandles
    cStatus.curHandles.forEach((h) => h.remove());
    cStatus.curHandles = [];
    if (!box || !box.elem || !(force || canHit(box))) return;
    // 设置curHandles
    let boxType = box.boxType || status.curBoxType;
    let w = box.elem.attrs.width;
    w = w > 40 ? 40 : w < 6 ? 6 : w; // 宽度从6~40，对应控制点半径从1.2到2.0
    let r = (1.2 + (w - 6) * 0.024) * (0.6 + data.ratio * 0.4);
    for (let i = 0; i < 8; i++) {
      let pt = self.getHandlePt(box.elem, i);
      let h = data.paper.circle(pt.x, pt.y, r).attr({
        'class': 'handle ' + boxType, 'stroke-width': r * 0.5,
      });
      cStatus.curHandles.push(h);
    }
  }

  function checkBoxes() {
    data.boxes.forEach((b) => self.removeClass(b, 'highlight'));
    let r = $.box.checkBoxCover();
    if (!r.status) {
      r.outBoxes.forEach((b) => self.addClass(b, 'highlight'));
      let boxIdxes = r.outBoxes.map((b) => b.idx);
      let tips = `检测到<b style="color:red">${r.msg}</b>并高亮显示，请修正。`;
      tips += `<a onclick="$.box.deleteBoxByIdxes([${boxIdxes}]);">批量删除高亮框</a>`;
      bsShow('错误', tips, 'warning', 5000);
    } else {
      bsHide();
    }
    return r;
  }

  function exportSubmitData() {
    let r = data.initRatio;
    let subColumns = {};
    let op = {blocks: [], columns: [], chars: [], images: []};
    let order = {blocks: [], columns: [], chars: [], images: []};
    data.boxes.forEach(function (box) {
      // s-deleted是系统删除，无需传给后台
      if (self.hasClass(box, 's-deleted')) return;
      // sub columns
      if (box.boxType === 'column' && box['sub_columns'])
        subColumns[box['column_id']] = box['sub_columns'];
      // order
      order[box.boxType + 's'].push([box.cid, box[box.boxType + '_id'] || '']);
      // op
      if (!box.op || !box.elem || !box.elem.attrs) return;
      let b = box.elem.attrs, p = {cid: box.cid, op: box.op};
      Object.assign(p, {
        x: self.round(b.x / r), y: self.round(b.y / r),
        w: self.round(b.width / r), h: self.round(b.height / r)
      });
      if (box.op === 'changed' && box.x === p.x && box.y === p.y && box.w === p.w && box.h === p.h) return;
      op[box.boxType + 's'].push(p);
    });
    return {op: op, order: order, sub_columns: subColumns};
  }

}());