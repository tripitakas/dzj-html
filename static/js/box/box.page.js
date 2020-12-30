/**
 * 切分校对-前端html页面操作函数
 */
(function () {
  'use strict';

  $.box.onBoxChanged(function (box, reason, param) {
    if (['recovered', 'added', 'deleted', 'changed'].indexOf(reason) > -1) {
      $.page.updateHeadBoxKindNo();
    }
    if (reason === 'recovered') {
      // 更新已删除字框数量（注：只有在"我的修改"状态下才可以看见、恢复已删除字框，且无法修改其它字框）
      $('.hint .deleted .no').text($('.box.deleted').length);
    }
    if (reason === 'switch') {
      $.page.updateFootCharInfo(box);
    }
    if (['recovered', 'added', 'deleted', 'changed', 'redo', 'undo'].indexOf(reason) > -1) {
      $.box.canRedo() ? $('#redo').removeClass('disabled') : $('#redo').addClass('disabled');
      $.box.canUndo() ? $('#undo').removeClass('disabled') : $('#undo').addClass('disabled');
    }
    if (['redo', 'undo'].indexOf(reason) > -1) {
      let boxBtn = $('#toggle-' + box.boxType);
      if (!boxBtn.hasClass('active')) boxBtn.click();
    }
  });

  let pStatus = {
    cut: {editBox: null, boxType: 'char'},      // 当前切分校对
    order: {noType: null, linkType: 'char'},    // 当前框序校对
  };

  $.page = {
    pStatus: pStatus,
    init: init,
    toggleNo: toggleNo,
    toggleLink: toggleLink,
    toggleMode: toggleMode,
    toggleBackBox: toggleBackBox,
    toggleCurShape: toggleCurShape,
    toggleCurBoxType: toggleCurBoxType,
    toggleHint: toggleHint,
    toggleMyHint: toggleMyHint,
    checkAndExport: checkAndExport,
    initHeadHintList: initHeadHintList,
    updateHeadBoxKindNo: updateHeadBoxKindNo,
    updateFootHintNo: updateFootHintNo,
    updateFootCharInfo: updateFootCharInfo,

  };

  function init(p) {
    // 1. 初始化
    $.box.initSvg(p.holder, p.imgUrl, p.width, p.height, p.showMode);
    $.box.setParam({userId: p.userId, readonly: p.readonly});
    // 2. 设置boxes
    $.box.setBoxes({
      chars: p.chars || [],
      blocks: p.blocks || [],
      columns: p.columns || [],
    });
    $.box.showBoxes(p.showBoxes || 'char');
    $.box.setCurBoxType(p.curBoxType || 'char');
    // 3. 设置图片
    $.box.toggleImage(p.showImage || true);
    $.box.setImageOpacity(p.blurImage || 0.2);
    if (!p.readonly) {
      $.box.initCut();
      $.box.initOrder();
      if (p.userLinks) $.box.oStatus.userLinks = p.userLinks;
      // 4. 设置字框大小窄扁等属性
      $.box.initCharKind();
      updateHeadBoxKindNo();
      // 5. 设置导航条中操作历史
      initHeadHintList();
    }
  }

  function checkAndExport() {
    // check
    if ($.box.isCutMode()) {
      let r = $.box.checkBoxes();
      if (!r.status) return {status: false};
      $.box.reorderBoxes();
      $.box.loadUserLinks();
    } else {
      let r = $.box.checkLinks();
      if (!r.status) {
        $.page.toggleLink(r.errorBoxType, true);
        return {status: false};
      }
      $.box.updateNoByLinks(r.links);
      $.box.updateUserLinks();
    }
    // export
    let ret = $.box.exportSubmitData();
    ret['user_links'] = $.box.oStatus.userLinks;
    ret['status'] = true;
    return ret;
  }

  function toggleMode(mode) {
    if (mode === $.box.status.boxMode) return;
    if (mode === 'order') { // 从切分校对切换为字序校对
      // 记录切分状态
      pStatus.cut.boxType = $.box.status.curBoxType;
      // 进入字序校对
      if ($.box.cStatus.hasChanged) {
        let r = $.box.checkBoxes();
        if (!r.status) return;
        $.box.reorderBoxes();
        $.box.loadUserLinks();
        $.box.cStatus.hasChanged = false;
        $.box.drawLink(true);
      }
      $('.m-header .left .title').text('字序校对');
      toggleNo(pStatus.order.noType, true);
      toggleLink(pStatus.order.linkType || 'char', true, true);
    } else { // 从字序校对切换为切分校对
      // 检查并更新线序link、更新序号no
      if ($.box.oStatus.hasChanged) {
        let r = $.box.checkLinks();
        if (!r.status) return;
        $.box.updateNoByLinks(r.links);
        $.box.updateUserLinks();
        $.box.oStatus.hasChanged = false;
      }
      // 记录字序状态
      pStatus.order.noType = $.box.status.curNoType;
      pStatus.order.linkType = $.box.oStatus.curLinkType;
      toggleNo(null, false);
      toggleLink(null, false);
      // 进入切分校对
      $('.m-header .left .title').text('切分校对');
      toggleCurBoxType(pStatus.cut.boxType, true);
    }
    $('.toggle-mode').removeClass('hide');
    $('#toggle-' + mode).addClass('hide');
    $('.m-header').removeClass('cut-mode order-mode').addClass(mode + '-mode');
    $($.box.data.holder).removeClass('cut-mode order-mode').addClass(mode + '-mode');
    $.box.status.boxMode = mode;
  }

  function toggleNo(boxType, show) {
    $('.toggle-no').removeClass('active');
    show && $('#toggle-no-' + boxType).addClass('active');
    $.box.toggleNo(boxType, show);
  }

  function toggleLink(boxType, show, navFirst) {
    $('.toggle-link').removeClass('active');
    show && $('#toggle-link-' + boxType).addClass('active');
    $.box.toggleLink(boxType, show);
    navFirst && $.box.switchCurBox($.box.findFirstBox(boxType));
    $.page.toggleBackBox($('#toggle-back-box').hasClass('active'));
  }

  function toggleBackBox(show) {
    $.page.toggleCurBoxType($.box.oStatus.curLinkType, show);
  }

  function toggleCurShape(shape, show) {
    $('.toggle-shape').removeClass('active');
    show && $('#toggle-' + shape).addClass('active');
    let holder = $($.box.data.holder);
    let names = holder.attr('class').split(' ');
    holder.attr('class', names.filter((n) => n.length && n.indexOf('shape-') < 0).join(' '));
    show && holder.addClass('shape-' + shape);
  }

  function toggleCurBoxType(boxType, show) {
    boxType = boxType || '';
    $('.toggle-box').removeClass('active');
    show && $('#toggle-' + boxType).addClass('active');
    $.box.switchBoxType(boxType, show);
    show && updateHeadBoxKindNo();
    updateFootHintNo();
    setStorage('toggleCutBox', show ? boxType : '');
  }

  function toggleHint(type, value) {
    if (type === 'ini') $.box.showIniHint();
    else if (type === 'cmb') $.box.showCmbHint();
    else if (type === 'usr') $.box.showUsrHint(value);
    else if (type === 'time') $.box.showTimeHint(value);
    $('#toggle-my-hint').removeClass('active');
    updateFootHintNo();
  }

  function toggleMyHint(userId, show) {
    if (show) {
      $.box.showMyHint(userId);
    } else {
      $.box.hideAllHint();
    }
    updateFootHintNo();
  }

  function updateHeadBoxKindNo() {
    let no = $.box.getBoxKindNo();
    console.log(no);
    $('#toggle-white .s-count').text(no.total || '');
    $('#toggle-opacity .s-count').text(no.total || '');
    $('#toggle-large .s-count').text(no.large || '');
    $('#toggle-small .s-count').text(no.small || '');
    $('#toggle-narrow .s-count').text(no.narrow || '');
    $('#toggle-flat .s-count').text(no.flat || '');
    $('#toggle-overlap .s-count').text(no.overlap || '');
    $('#toggle-mayWrong .s-count').text(no.mayWrong || '');
  }

  function initHeadHintList() {
    if (!$('#hint-list').length) return;
    $.box.initUserAndTime();
    let html = '';
    if ($.box.eStatus.users.length) {
      html += '<li class="divider"></li>';
      $.box.eStatus.users.forEach(function (item) {
        let a = `<a href="#">${item.username} 的修改</a>`;
        html += `<li class="usr-hint hint" onclick="$.page.toggleHint('usr','${item.user_id}')">${a}</li>`;
      });
    }
    if ($.box.eStatus.times.length) {
      html += '<li class="divider"></li>';
      $.box.eStatus.times.forEach(function (item) {
        let a = `<a href="#">${item.create_time + '@' + item.username}</a>`;
        html += `<li class="time-hint hint" onclick="$.page.toggleHint('time','${item.create_time}')">${a}</li>`;
      });
    }
    if (html) $('#hint-list').append(html);
  }

  function updateFootHintNo() {
    if ($.box.eStatus.hint.type) {
      let no = $.box.getHintNo();
      $('.m-footer .hint-info .added .s-no').text(no.added || 0);
      $('.m-footer .hint-info .deleted .s-no').text(no.deleted || 0);
      $('.m-footer .hint-info .changed .s-no').text(no.changed || 0);
      $('.m-footer .hint-info').removeClass('hide');
    } else {
      $('.m-footer .hint-info').addClass('hide');
    }
  }

  function updateFootCharInfo(box) {
    if (box) {
      let t = {char: '字框', column: '列框', block: '栏框'};
      $('.m-footer .char-name').text(`${t[box.boxType]}#${box.cid}#${box[box.boxType + '_id'] || ''}`);
      let info = `${box.txt || box['ocr_txt'] || ''}${box['is_small'] ? '(夹注小字)' : ''}${box.readonly ? '/只读' : ''}`;
      $('.m-footer .char-info').text(info);
    } else {
      $('.m-footer .char-name').text('未选中');
      $('.m-footer .char-info').text('');
    }
  }

}());