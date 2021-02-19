/**
 * box.base.js扩展
 * 1. 操作痕迹。包括初始状态、某用户或时间的操作痕迹、所有操作痕迹、最终状态等
 * 2. redo/undo
 * Date: 2020-11-28
 */
(function () {
  'use strict';

  $.box.onBoxChanged(function (box, reason, param) {
    if ('added/changed/deleted/recovered'.indexOf(reason) > -1) {
      $.box.eStatus.doLogs.push([box, reason, param]);
      // $.box.eStatus.undoLogs = [];
    }
    if ('added/changed'.indexOf(reason) > -1) {
      let boxes = Array.isArray(box) ? box : [box];
      boxes.forEach(function (box) {
        $.box.updateCharShape(box);
        $.box.updateBoxOverlap(box);
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
    mayWrong: '',                                 // 易错字列表
    charMeanA: 0,                                 // 字框的平均面积
    hint: {type: 0, boxTypes: [], user_id: 0, create_time: 0},  // 当前hint
  };

  $.extend($.box, {
    eStatus: eStatus,
    undo: undo,
    redo: redo,
    canUndo: canUndo,
    canRedo: canRedo,
    getHintNo: getHintNo,
    showMyHint: showMyHint,
    hideAllHint: hideAllHint,
    showUserHint: showUserHint,
    showInitHint: showInitHint,
    showCombHint: showCombHint,
    showTimeHint: showTimeHint,
    initUserAndTime: initUserAndTime,
    resetOverlap: resetOverlap,
    getBoxKindNo: getBoxKindNo,
    initCharKind: initCharKind,
    updateMayWrong: updateMayWrong,
    updateCharShape: updateCharShape,
    updateBoxOverlap: updateBoxOverlap,
  });

  //-------1.修改痕迹-------
  // 修改痕迹的切换是通过在holder上设置不同的css样式来实现的
  // 包括：初始状态init-hint、用户痕迹user-hint、时间痕迹time-hint、综合修改comb-hint等

  // 比较两个时间的大小
  function cmpTime(a, b) {
    a = typeof a === 'object' ? a.create_time : a;
    b = typeof b === 'object' ? b.create_time : b;
    return new Date(a || '1970-01-01') - new Date(b || '1970-01-01');
  }

  // 设置字框中的用户和时间信息
  function initUserAndTime() {
    let users = {}, times = {};
    data.boxes.forEach(function (box) {
      let logs = box['box_logs'] || [];
      if (!logs.length) return;
      box['box_logs'] = logs.sort(cmpTime);
      box['box_logs'].forEach(function (log) {
        let item = {user_id: log.user_id, username: log.username, create_time: log.create_time};
        if (log.user_id && !users[log.user_id]) users[log.user_id] = item;
        if (log.create_time && !times[log.create_time]) times[log.create_time] = item;
      });
    });
    if (users) eStatus.users = Object.values(users).sort(cmpTime);
    if (times) eStatus.times = Object.values(times).sort(cmpTime);
  }

  // 设置初始状态
  // 不显示新增框；有修改则显示第一条log；无则设置为ini-hint
  function showInitHint() {
    status.readonly = true;
    $(data.holder).addClass('show-hint init-hint').removeClass('user-hint comb-hint time-hint');
    if (eStatus.hint.type === 'init') return;
    data.boxes.forEach(function (box) {
      box.hint && box.hint.elem && box.hint.elem.remove();
      box.hint && box.hint.former && box.hint.former.remove();
      if (box.added) return;
      let logs = box['box_logs'] || [];
      if (!logs.length) return self.addClass(box, 'ini-hint');
      box.hint = {elem: self.createBox(logs[0].pos, `box ${box.boxType} hint h-init`)};
    });
    eStatus.hint.type = 'init';
  }

  // 设置某时间点所有修改痕迹
  // 1. 如果字框无修改历史，显示字框当前状态
  // 2. 否则，如果字框在这个时间点有修改，则显示这个时间点的修改状态和修改前的状态
  // 3. 否则，如果显示字框在这个时间点前有logs，则显示最后log的状态
  // 4. 否则，如果显示字框在这个时间点后有logs，如果框不是新增则显示
  function showTimeHint(create_time) {
    status.readonly = true;
    $(data.holder).addClass('show-hint time-hint').removeClass('init-hint comb-hint user-hint');
    if (eStatus.hint.type === 'time' && eStatus.hint.create_time === create_time) return;
    let boxTypes = [];
    data.boxes.forEach(function (box) {
      let logs = box['box_logs'] || [], hint = box.hint || {};
      if (!logs.length) return self.addClass(box, 'box-hint'); // #1
      self.removeClass(box, 'box-hint');
      hint.elem && hint.elem.remove();
      hint.former && hint.former.remove();
      let curLogs = logs.filter((log) => log['create_time'] === create_time);
      let prevLogs = logs.filter((log) => cmpTime(log, create_time) < 0);
      if (curLogs.length) { // #2
        if (boxTypes.indexOf(box.boxType) < 0) boxTypes.push(box.boxType);
        hint.create_time = create_time;
        hint.elem = self.createBox(curLogs[0].pos, `box ${box.boxType} hint h-${curLogs[0].op}`);
        let idx = logs.indexOf(curLogs[0]);
        if (idx > 0 && curLogs[0].op === 'changed') {
          hint.former = self.createBox(logs[idx - 1].pos, `box ${box.boxType} hint h-former`);
        }
      } else if (prevLogs.length) { // #3
        let last = prevLogs[prevLogs.length - 1];
        if (last.op !== 'deleted')
          hint.elem = self.createBox(last.pos, `box ${box.boxType} hint`);
      } else if (!box.added) { // #4
        self.addClass(box, 'box-hint');
      }
      box.hint = hint;
    });
    Object.assign(eStatus.hint, {type: 'time', create_time: create_time, boxTypes: boxTypes});
  }

  // 设置用户所有修改痕迹
  // 如果有用户修改，则显示修改痕迹，否则设置为box-hint
  function showUserHint(user_id) {
    status.readonly = true;
    $(data.holder).addClass('show-hint user-hint').removeClass('init-hint comb-hint time-hint');
    if (eStatus.hint.type === 'user' && eStatus.hint.user_id === user_id) return;
    let boxTypes = [];
    data.boxes.forEach(function (box) {
      let logs = box['box_logs'] || [], hint = box.hint || {};
      let uLogs = logs.filter((log) => log['user_id'] === user_id);
      if (uLogs.length) {
        if (boxTypes.indexOf(box.boxType) < 0) boxTypes.push(box.boxType);
        self.removeClass(box, 'box-hint');
        let log = uLogs[uLogs.length - 1];
        if (hint.user_id === user_id && hint.create_time === log.create_time) return;
        hint.elem && hint.elem.remove();
        hint.former && hint.former.remove();
        hint.elem = self.createBox(log.pos, `box ${box.boxType} hint h-${log.op}`);
        let idx = logs.indexOf(log);
        if (idx > 0 && log.op === 'changed') {
          hint.former = self.createBox(logs[idx - 1].pos, `box ${box.boxType} hint h-former`);
        }
        hint.create_time = log.create_time;
        hint.user_id = log.user_id;
        box.hint = hint;
      } else {
        self.addClass(box, 'box-hint');
        hint.elem && hint.elem.remove();
        hint.former && hint.former.remove();
        box.hint = {};
      }
    });
    Object.assign(eStatus.hint, {type: 'user', user_id: user_id, boxTypes: boxTypes});
  }

  // 设置用户当前操作痕迹，包括历史操作和当前操作
  function showMyHint(user_id) {
    status.readonly = true;
    $(data.holder).addClass('show-hint user-hint').removeClass('init-hint comb-hint time-hint');
    if (eStatus.hint.type === 'my') return;
    showUserHint(user_id);
    data.boxes.forEach(function (box) {
      if (!box.op) return;
      if (eStatus.hint.boxTypes.indexOf(box.boxType) < 0) eStatus.hint.boxTypes.push(box.boxType);
      self.addClass(box, 'box-hint h-' + box.op);
      box.hint && box.hint.elem && box.hint.elem.remove();
      box.hint && box.hint.former && box.hint.former.remove();
      if (box.op === 'changed') {
        box.hint = {former: self.createBox(box, 'hint h-former')};
      }
    });
    eStatus.hint.type = 'my';
  }

  // 显示框的综合修改痕迹
  function showCombHint() {
    $(data.holder).addClass('comb-hint').removeClass('show-hint user-hint init-hint time-hint');
    status.readonly = true;
    eStatus.hint.type = 'comb';
  }

  // 隐藏所有修改痕迹
  function hideAllHint() {
    $(data.holder).removeClass('show-hint init-hint comb-hint user-hint time-hint');
    status.readonly = false;
  }

  // 获取增删改操作的数量
  function getHintNo() {
    let boxType = status.curBoxType;
    if (!boxType) return {};
    if (boxType === 'all') boxType = 'box';
    if (['user', 'time', 'my'].indexOf(eStatus.hint.type) > -1) // 某个用户、时间操作
      return {
        deleted: $('.' + boxType + '.h-deleted').length,
        added: $('.' + boxType + '.h-added:not(.h-deleted)').length,
        changed: $('.' + boxType + '.h-changed:not(.h-added):not(.h-deleted)').length
      };
    else if (eStatus.hint.type === 'comb')  // 总的字框操作
      return {
        added: $('.' + boxType + '.b-added').length,
        deleted: $('.' + boxType + '.b-deleted:not(.b-added)').length,
        changed: $('.' + boxType + '.b-changed:not(.b-added):not(.b-deleted)').length
      };
    else
      return {};
  }

  //-------2.框大小窄扁及重叠-------
  // 初始化计算字框的各种属性
  // 易错字列表：一二三士土王五夫去七十千不示入人八上下卜于干子今令雷電目岱支生品卷雲竺巨公金世甲
  function initCharKind() {
    // init param
    let sizes = data.boxes.filter((b) => b.boxType === 'char' && !b.deleted && b.w && b.h)
        .map((b) => b.w * b.h).sort((a, b) => b - a);
    eStatus.charMeanA = sizes.length > 5 ? sizes[4] : sizes[0];

    // 1.大小窄扁、易错字
    data.boxes.forEach(function (b, i) {
      if (b.boxType === 'char' && !self.isDeleted(b)) {
        let shape = getCharShape(b, true);
        shape && self.addClass(b, shape);
        let txt = eStatus.mayWrong && self.getCharTxt(b);
        if (txt && eStatus.mayWrong.indexOf(txt) > -1) {
          self.addClass(b, 's-mayWrong');
        }
      }
    });

    // 2.重叠
    for (let i = 0, len = data.boxes.length; i < len; i++) {
      let b = data.boxes[i];
      if (self.isDeleted(b)) continue;
      for (let j = i + 1; j < len; j++) {
        let b1 = data.boxes[j];
        if (self.isDeleted(b1) || b1.boxType !== b.boxType) continue;
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
      total: $('.box.' + boxType + ':not(.s-deleted):not(.b-deleted):not(.u-deleted)').length,
      flat: $('.box.' + boxType + '.s-flat:not(.s-deleted):not(.b-deleted):not(.u-deleted)').length,
      large: $('.box.' + boxType + '.s-large:not(.s-deleted):not(.b-deleted):not(.u-deleted)').length,
      small: $('.box.' + boxType + '.s-small:not(.s-deleted):not(.b-deleted):not(.u-deleted)').length,
      narrow: $('.box.' + boxType + '.s-narrow:not(.s-deleted):not(.b-deleted):not(.u-deleted)').length,
      overlap: $('.box.' + boxType + '.s-overlap:not(.s-deleted):not(.b-deleted):not(.u-deleted)').length,
      mayWrong: $('.box.' + boxType + '.s-mayWrong:not(.s-deleted):not(.b-deleted):not(.u-deleted)').length,
    };
  }

  // 如果initial，则根据box原始的的w/h参数计算，否则，根据box.elem的坐标转换后计算
  function getCharShape(box, initial) {
    if (box.boxType !== 'char') return;
    let p = box.elem && box.elem.attrs;
    if (!initial) box = {w: p.width / data.initRatio, h: p.height / data.initRatio};
    if (!box.w) return;
    if (box.w * box.h > eStatus.charMeanA * 1.5) return 's-large';
    let small = '';
    if (box['is_small'] || box.w * box.h < eStatus.charMeanA * 0.6) small = ' s-small';
    if (box.w / box.h < 0.67) return 's-narrow' + small;
    if (box.h / box.w < 0.67) return 's-flat' + small;
    return small;
  }

  function updateCharShape(box) {
    if (box.boxType !== 'char') return;
    let cNames = box.elem.attr('class').split(' ');
    let cls = cNames.filter((s) => s.length && s.indexOf('s-') < 0).join(' ');
    box.elem.attr({'class': $.trim(cls + ' ' + (getCharShape(box) || ''))});
  }

  // 重置overlap属性
  function resetOverlap(boxType) {
    let boxes = self.getBoxes()[boxType];
    boxes.forEach((b) => {
      b.overlap = [];
      self.removeClass(b, 's-overlap').overlap = [];
    });
    for (let i = 0, len = boxes.length; i < len; i++) {
      let b = boxes[i];
      if (self.isDeleted(b)) continue;
      for (let j = i + 1; j < len; j++) {
        let b1 = boxes[j];
        if (self.isDeleted(b1) || b1.boxType !== b.boxType) continue;
        if (self.isOverlap(b, b1)) {
          b.overlap = (b.overlap || []).concat([b1.idx]);
          b1.overlap = (b1.overlap || []).concat([b.idx]);
          self.addClass(b, 's-overlap');
          self.addClass(b1, 's-overlap');
        }
      }
    }
  }

  function updateBoxOverlap(b) {
    if (self.isDeleted(b)) return;
    b.overlap = [];
    for (let i = 0, len = data.boxes.length; i < len; i++) {
      let b1 = data.boxes[i];
      if (self.isDeleted(b1) || b1.boxType !== b.boxType || b1.idx === b.idx) continue;
      if (self.isOverlap(b, b1)) {
        b.overlap = b.overlap.concat([b1.idx]);
        b1.overlap = (b1.overlap || []).concat([b.idx]);
        self.addClass(b1, 's-overlap');
      } else if (b1.overlap && b1.overlap.indexOf(b.idx) > -1) {
        b1.overlap = b1.overlap.filter((j) => j !== b.idx);
        if (!b1.overlap.length) self.removeClass(b1, 's-overlap');
      }
    }
    self.toggleClass(b, 's-overlap', b.overlap.length);
  }

  function updateMayWrong(mayWrong) {
    eStatus.mayWrong = mayWrong;
    mayWrong && data.boxes.forEach(function (b, i) {
      if (b.boxType === 'char' && !self.isDeleted(b)) {
        let txt = self.getCharTxt(b);
        if (txt && mayWrong.indexOf(txt) > -1) {
          self.addClass(b, 's-mayWrong');
        } else {
          self.removeClass(b, 's-mayWrong');
        }
      }
    });
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
    self.switchBoxType(boxes[0].boxType, true);
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
