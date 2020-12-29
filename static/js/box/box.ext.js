/**
 * box.core.js扩展
 * 1. 操作痕迹。包括初始状态、某用户或时间的操作痕迹、所有操作痕迹、最终状态等
 * 2. redo/undo
 * Date: 2020-11-28
 */
(function () {
  'use strict';

  $.box.onBoxChanged(function (box, reason, param) {
    if ('added/changed/deleted/recovered'.indexOf(reason) > -1) {
      $.box.eStatus.doLogs.push([box, reason, param]);
      $.box.eStatus.undoLogs = [];
    }
    if ('added/changed'.indexOf(reason) > -1) {
      let boxes = Array.isArray(box) ? box : [box];
      boxes.forEach(function (box) {
        $.box.updateCharShape(box);
        $.box.updateCharOverlap(box);
      });
    }
  });

  let self = $.box;
  let data = self.data;
  let status = self.status;
  let eStatus = {
    users: [],                                    // 日志中的用户信息
    times: [],                                    // 日志中的时间信息
    doLogs: [],                                   // 增删改等do操作堆栈
    undoLogs: [],                                 // undo操作堆栈
    charMean: {w: 0, h: 0, a: 0},                 // 字框的平均长、宽和面积
    hint: {type: 0, user_id: 0, create_time: 0},  // 当前hint，type可为usr/ini/cmb
  };

  $.extend($.box, {
    eStatus: eStatus,
    undo: undo,
    redo: redo,
    canUndo: canUndo,
    canRedo: canRedo,
    getHintNo: getHintNo,
    showMyHint: showMyHint,
    showUsrHint: showUsrHint,
    showIniHint: showIniHint,
    showCmbHint: showCmbHint,
    hideAllHint: hideAllHint,
    showTimeHint: showTimeHint,
    initUserAndTime: initUserAndTime,
    switchBoxType: switchBoxType,
    getBoxKindNo: getBoxKindNo,
    initCharKind: initCharKind,
    updateCharShape: updateCharShape,
    updateCharOverlap: updateCharOverlap,
  });

  //-------1.操作痕迹-------
  // 设置字框中的用户和时间信息
  function initUserAndTime() {
    let users = {}, times = {};
    data.boxes.forEach(function (box) {
      (box['box_logs'] || []).forEach(function (log) {
        let item = {user_id: log.user_id, username: log.username, create_time: log.create_time};
        if (log.user_id && !users[log.user_id]) users[log.user_id] = item;
        if (log.create_time && !times[log.create_time]) times[log.create_time] = item;
      });
    });
    let sort = (a, b) => new Date(a.create_time) - new Date(b.create_time);
    if (users) eStatus.users = Object.values(users).sort(sort);
    if (times) eStatus.times = Object.values(times).sort(sort);
  }

  // 根据log设置操作痕迹
  function setLogHint(user_id, create_time) {
    let value = user_id ? user_id : create_time;
    let key = user_id ? 'user_id' : 'create_time';
    data.boxes.forEach(function (box) {
      let hint = box.hint || {};
      hint.elem && hint.elem.remove();
      let logs = (box['box_logs'] || []).filter((log) => log[key] === value);
      if (logs.length) {
        let log = logs[logs.length - 1];
        let cls = 'box ' + box.boxType + ' hint h-' + log.op;
        hint.elem = self.createBox(log.pos, cls);
        hint.create_time = log.create_time;
        hint.user_id = log.user_id;
        box.hint = hint;
      }
    });
  }

  // 根据用户当前op设置操作痕迹
  function setOpHint() {
    data.boxes.forEach(function (box) {
      if (!box.op) return;
      let hint = box.hint || {};
      hint.elem && hint.elem.remove();
      hint.elem = box.elem.clone();
      hint.elem.attr({'class': 'box ' + box.boxType + ' hint h-' + box.op});
      box.hint = hint;
    });
  }

  // 显示某时间的修改痕迹
  function showTimeHint(create_time) {
    // 操作痕迹的切换是通过在holder上设置不同的css样式来实现，有usr-hint、ini-hint、cmb-hint等
    $(data.holder).addClass('usr-hint').removeClass('ini-hint').removeClass('cmb-hint');
    setLogHint(null, create_time);
    eStatus.hint = {type: 'time', create_time: create_time};
    status.readonly = true;
  }

  // 显示某用户的操作痕迹
  function showUsrHint(user_id) {
    $(data.holder).addClass('usr-hint').removeClass('ini-hint').removeClass('cmb-hint');
    setLogHint(user_id);
    eStatus.hint = {type: 'usr', user_id: user_id};
    status.readonly = true;
  }

  // 显示我的操作痕迹
  function showMyHint(user_id) {
    $(data.holder).addClass('usr-hint').removeClass('ini-hint').removeClass('cmb-hint');
    setLogHint(user_id);
    setOpHint(); // 先设置logHint，后设置opHint，以免被冲掉
    eStatus.hint = {type: 'usr', user_id: user_id};
    status.readonly = true;
  }

  // 显示框的初始状态
  function showIniHint() {
    $(data.holder).addClass('ini-hint').removeClass('usr-hint').removeClass('cmb-hint');
    data.boxes.forEach(function (box) {
      let boxLogs = box['box_logs'];
      if (boxLogs && !box.added && !box.iniElem) {
        let cls = 'box init ' + box.boxType + (self.hasClass(box, 'even') ? ' even' : ' odd');
        box.iniElem = self.createBox(boxLogs[0].pos, cls);
      }
    });
    eStatus.hint = {type: 'ini'};
    status.readonly = true;
  }

  // 显示框的综合修改痕迹
  function showCmbHint() {
    $(data.holder).addClass('cmb-hint').removeClass('usr-hint').removeClass('ini-hint');
    eStatus.hint = {type: 'cmb'};
    status.readonly = true;
  }

  // 隐藏所有修改痕迹
  function hideAllHint() {
    $(data.holder).removeClass('cmb-hint').removeClass('usr-hint').removeClass('ini-hint');
    eStatus.hint = {type: 0};
    status.readonly = false;
  }

  // 获取增删改操作的数量
  function getHintNo() {
    let box = status.curBoxType || 'box';
    if (['usr', 'time'].indexOf(eStatus.hint.type) > -1) // 某个用户、时间操作
      return {
        deleted: $('.' + box + '.h-deleted').length,
        added: $('.' + box + '.h-added:not(.h-deleted)').length,
        changed: $('.' + box + '.h-changed:not(.h-added):not(.h-deleted)').length
      };
    else if (eStatus.hint.type === 'cmb')  // 总的字框操作
      return {
        added: $('.' + box + '.b-added').length,
        deleted: $('.' + box + '.b-deleted:not(.b-added)').length,
        changed: $('.' + box + '.b-changed:not(.b-added):not(.b-deleted)').length
      };
    else
      return {};
  }

  //-------2.框大小窄扁及重叠-------
  // 切换显示框类型，包括all/block/column/char
  function switchBoxType(boxType, show) {
    $.box.setCurBoxType(boxType);
    let holder = $($.box.data.holder);
    holder.removeClass('hide-all show-all show-block show-column show-char');
    if (show && boxType) {
      $.box.setCurBoxType(boxType === 'all' ? '' : boxType);
      holder.addClass('show-' + boxType);
    } else {
      holder.addClass('hide-all');
    }
  }

  // 初始化计算字框的各种属性
  function initCharKind() {
    // 1.大小窄扁、易错
    setCharMean();
    let mayWrongChars = '一二三士土王五夫去七十千不示入人八上下卜于干子今令雷電目岱支生品卷雲竺巨公金世甲';
    data.boxes.forEach(function (b, i) {
      if (b.boxType === 'char' && !self.isDeleted(b)) {
        let shape = getCharShape(b, true);
        shape && self.addClass(b, shape);
        let txt = self.getTxt(b);
        if (txt && mayWrongChars.indexOf(txt) > -1) {
          self.addClass(b, 's-mayWrong');
        }
      }
    });
    // 2.重叠
    for (let i = 0, len = data.boxes.length; i < len; i++) {
      let b = data.boxes[i];
      if (b.boxType !== 'char' || self.isDeleted(b)) continue;
      for (let j = i + 1; j < len; j++) {
        let b1 = data.boxes[j];
        if (b1.boxType !== 'char' || self.isDeleted(b1)) continue;
        if (self.isOverlap(b, b1)) {
          b.overlap = (b.overlap || []).concat([b1.idx]);
          b1.overlap = (b1.overlap || []).concat([b.idx]);
          self.addClass(b, 's-overlap');
          self.addClass(b1, 's-overlap');
        }
      }
    }
  }

  // 获取框大小窄扁、重叠等的数量
  function getBoxKindNo() {
    let boxType = status.curBoxType;
    if (['char', 'column', 'block'].indexOf(boxType) < 0) return {};
    return {
      total: $('.' + boxType + ':not(.b-deleted):not(.u-deleted)').length,
      flat: $('.' + boxType + '.s-flat:not(.b-deleted):not(.u-deleted)').length,
      large: $('.' + boxType + '.s-large:not(.b-deleted):not(.u-deleted)').length,
      small: $('.' + boxType + '.s-small:not(.b-deleted):not(.u-deleted)').length,
      narrow: $('.' + boxType + '.s-narrow:not(.b-deleted):not(.u-deleted)').length,
      overlap: $('.' + boxType + '.s-overlap:not(.b-deleted):not(.u-deleted)').length,
      mayWrong: $('.' + boxType + '.s-mayWrong:not(.b-deleted):not(.u-deleted)').length,
    };
  }

  function setCharMean(reset) {
    if (!reset && eStatus.charMean.w) return;
    let length = 0, sum = {w: 0, h: 0, a: 0};
    data.boxes.forEach(function (box) {
      if (box.boxType === 'char' && !box.deleted && box.w && box.h) {
        length++;
        sum.w += box.w || 0;
        sum.h += box.h || 0;
        sum.a += (box.w * box.h) || 0;
      }
    });
    // set mean
    eStatus.charMean.w = sum.w / length;
    eStatus.charMean.h = sum.h / length;
    eStatus.charMean.a = sum.a / length;
  }

  // 如果initial，则根据box原始的的w/h参数计算，否则，根据box.elem的坐标转换后计算
  function getCharShape(box, initial) {
    if (box.boxType !== 'char' || !box.w) return;
    if (box['is_small']) return 's-small';
    let p = box.elem && box.elem.attrs;
    if (!initial) box = {w: p.width / data.initRatio, h: p.height / data.initRatio};
    // shape的class均以s-开头
    if (box.w * box.h > eStatus.charMean.a * 1.5) return 's-large';
    if (box.w * box.h < eStatus.charMean.a * 0.36) return 's-small';
    if (box.w < eStatus.charMean.w * 0.5) return 's-narrow';
    if (box.h < eStatus.charMean.h * 0.5) return 's-flat';
  }

  function updateCharShape(box) {
    if (box.boxType !== 'char') return;
    let cNames = box.elem.attr('class').split(' ');
    let cls = cNames.filter((s) => s.length && s.indexOf('s-') < 0).join(' ');
    box.elem.attr({'class': $.trim(cls + ' ' + (getCharShape(box) || ''))});
  }

  function updateCharOverlap(b) {
    let len = data.boxes.length;
    if (b.boxType !== 'char' || self.isDeleted(b)) return;
    for (let i = 0; i < len; i++) {
      let b1 = data.boxes[i];
      if (b1.boxType !== 'char' || self.isDeleted(b1) || b1.idx === b.idx) continue;
      if (self.isOverlap(b, b1)) {
        b.overlap = (b.overlap || []).concat([b1.idx]);
        b1.overlap = (b1.overlap || []).concat([b.idx]);
        self.addClass(b, 's-overlap');
        self.addClass(b1, 's-overlap');
      } else if (b1.overlap && b1.overlap.indexOf(b.idx) > -1) {
        b1.overlap = b1.overlap.filter((j) => j !== b.idx);
        if (!b1.overlap.length) self.removeClass(b1, 's-overlap');
      }
    }
  }

  //-------3.undo/redo-------
  function canUndo() {
    return !!eStatus.doLogs.length;
  }

  function undo() {
    if (!canUndo()) return;
    let log = eStatus.doLogs.pop();
    let box = log[0], reason = log[1], param = log[2] || {};
    let boxes = Array.isArray(box) ? box : [box];
    switchBoxType(boxes[0].boxType, true);
    if (reason === 'added') {
      self.addClass(box, 's-deleted'); // 标记而不实际删除
    }
    if (reason === 'recovered') {
      boxes.forEach((box) => self.deleteBox(box, true));
    }
    if (reason === 'deleted') {
      boxes.forEach((box) => self.recoverBox(box, true));
      if (boxes.length === 1) self.switchCurBox(boxes[0]);
    }
    if (reason === 'changed') {
      boxes.forEach((box) => self.unChangeBox(box, param));
      if (boxes.length === 1) self.switchCurBox(boxes[0]);
    }
    eStatus.undoLogs.push(log);
    self.notifyChanged(box, 'undo', param);
  }

  function canRedo() {
    return !!eStatus.undoLogs.length;
  }

  function redo() {
    if (!canRedo()) return;
    let log = eStatus.undoLogs.pop();
    let box = log[0], reason = log[1], param = log[2] || {};
    let boxes = Array.isArray(box) ? box : [box];
    if (reason === 'added') {
      self.removeClass(box, 's-deleted');
      if (boxes.length === 1) self.switchCurBox(boxes[0]);
    }
    if (reason === 'recovered') {
      boxes.forEach((box) => self.recoverBox(box, true));
      if (boxes.length === 1) self.switchCurBox(boxes[0]);
    }
    if (reason === 'deleted') {
      boxes.forEach((box) => self.deleteBox(box, true));
    }
    if (reason === 'changed') {
      boxes.forEach((box) => self.changeBox(box, param));
      if (boxes.length === 1) self.switchCurBox(boxes[0]);
    }
    eStatus.doLogs.push(log);
    self.notifyChanged(box, 'undo', param);
  }

}());
