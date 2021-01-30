/**
 @desc 切分相关操作
 */
//----------------------图片操作----------------------
// 显隐图片
$('#toggle-img').on('click', function () {
  $(this).toggleClass('active');
  $.box.toggleImage($('#toggle-img').hasClass('active'));
});

// 模糊图片
$('#toggle-blur').on('click', function () {
  $(this).toggleClass('active');
  $.box.setImageOpacity($(this).hasClass('active') ? 0.2 : 1);
});

// 缩小图片
$('#zoom-out').on('click', function () {
  $.box.zoomImg(null, 0.9);
});

// 放大图片
$('#zoom-in').on('click', function () {
  $.box.zoomImg(null, 1.1);
});

// 原始大小
$('#zoom-reset').on('click', function () {
  $.box.zoomImg(1);
});


//----------------------系统操作----------------------
// 查看page
$('.m-footer .page-name').on('click', function () {
  if ($(this).hasClass('disabled')) return;
  let url = '/page/' + $(this).text();
  let charName = $('.m-footer .char-name').text();
  if (charName && charName.length && charName !== '未选中') {
    url += '?cid=' + charName.split('#')[1];
  }
  window.open(url, '_blank');
});

// 查看char
$('.m-footer .char-name').on('click', function () {
  let charName = $(this).text();
  if ($(this).hasClass('disabled') || charName === '未选中') return;
  if (!/b\dc\d+c\d+/.test(charName))
    return bsShow('提示', '当前不是字框，无法查看', 'warning', 1000);
  if (charName.indexOf('#') > -1) {
    let pageName = $('.m-footer .page-name').text();
    charName = pageName + '_' + charName.split('#')[1];
  }
  window.open('/char/' + charName, '_blank');
});

// 恢复初始设置
$('#btn-reset').on('click', function () {
  $.box.zoomImg(1);
  $.box.toggleImage(true);
  $.box.setImageOpacity(0.2);
  if ($.box.isCutMode()) {
    $('#no-hint').click();
    $.page.toggleCurShape('', false);
    if (!$('#toggle-char').hasClass('active')) $('#toggle-char').click();
    if ($('#toggle-no-char').hasClass('active')) $('#toggle-no-char').click();
    if ($('#toggle-multi').hasClass('active')) $('#toggle-multi').click();
  } else {
    $.page.toggleNo('', false);
    $('.toggle-no').removeClass('active');
    if (!$('#toggle-link-char').hasClass('active')) $('#toggle-link-char').click();
    if ($('#toggle-back-box').hasClass('active')) $('#toggle-back-box').click();
  }
});

// 检查、应用修改
$('#btn-check').on('click', function () {
  if ($.box.isCutMode()) { // 检查框外框
    let r = $.box.checkBoxes();
    if (r.status) {
      if ($.box.cStatus.hasChanged) {
        $.box.reorderBoxes();
        $.box.loadUserLinks();
        $.box.showNo();
      }
      bsShow('成功', '检查无误!', 'info', 500);
    }
  } else { // 检查序线，并更新序号
    let r = $.box.checkLinks();
    if (!r.status) {
      $.page.toggleLink(r.errorBoxType, true);
    } else {
      if ($.box.oStatus.hasChanged) {
        $.box.updateNoByLinks(r.links);
        $.box.showNo();
      }
      bsShow('成功', '检查无误', 'info', 500);
    }
  }
});

// 切换切分、字序模式
$('.toggle-mode').on('click', function () {
  $.page.toggleMode($(this).attr('id').replace('toggle-', ''));
});


//----------------------切分操作----------------------
// 更多框操作
$('#toggle-box-more').on('click', function () {
  if (!$.box.isCutMode()) return;
  $('#box-op').toggleClass('hide');
});

// 切换蒙白、透视、大小窄扁、重叠等属性
$('.toggle-shape').on('click', function () {
  if (!$.box.isCutMode()) return;
  $(this).toggleClass('active');
  $.page.toggleCurShape($(this).attr('id').replace('toggle-', ''), $(this).hasClass('active'));
});

// 显隐栏框、列框、字框、图框、所有
$('.toggle-box').on('click', function () {
  $(this).toggleClass('active');
  $.page.toggleCurBoxType($(this).attr('id').replace('toggle-', ''), $(this).hasClass('active'));
});

// 系统配置
$('#cut-config').on('click', function () {
  $('#pageConfigModal .may_wrong').text($.box.eStatus.mayWrong);
  $('#pageConfigModal .img_opacity').val($.box.getImageOpacity());
  $('#pageConfigModal').modal();
});

$('#pageConfigModal .modal-confirm').on('click', function () {
  // 易错字列表
  let mayWrong = $('#pageConfigModal .may_wrong').val().trim();
  if ($.box.eStatus.mayWrong !== mayWrong) {
    if (!$('#toggle-mayWrong').hasClass('active')) $('#toggle-mayWrong').click();
    $.box.updateMayWrong(mayWrong);
    setStorage('mayWrong', mayWrong);
  }
  // 图片模糊
  let imgOpacity = $('#pageConfigModal .img_opacity').val().trim();
  if (imgOpacity) {
    if (imgOpacity !== '1' && !/0.\d+/.test(imgOpacity))
      return showError('错误', '请输入0-1之间的数字', 1000);
    if (imgOpacity !== $.box.getImageOpacity()) {
      $.box.setImageOpacity(imgOpacity);
      setStorage('imgOpacity', imgOpacity);
    }
  }
});

// 自适应调整栏框
$('#adjust-blocks').on('click', function () {
  if (!$.box.isCutMode()) return;
  if (!$('#toggle-block').hasClass('active')) $('#toggle-block').click();
  setTimeout(() => {
    $.box.adjustBoxes('blocks');
    $.box.resetOverlap('blocks');
    bsShow('成功', '已重新调整', 'info', 500);
  }, 500);
});

// 自适应调整列框
$('#adjust-columns').on('click', function () {
  if (!$.box.isCutMode()) return;
  if (!$('#toggle-column').hasClass('active')) $('#toggle-column').click();
  setTimeout(() => {
    $.box.adjustBoxes('columns');
    $.box.resetOverlap('columns');
    bsShow('成功', '已重新调整', 'info', 500);
  }, 500);
});

// 撤销
$('#undo').on('click', function () {
  if (!$.box.isCutMode()) return;
  $.box.undo();
});

// 重做
$('#redo').on('click', function () {
  if (!$.box.isCutMode()) return;
  $.box.redo();
});

// 多选模式
$('#toggle-multi').on('click', function () {
  if (!$.box.isCutMode()) return;
  $(this).toggleClass('active');
  $.box.toggleMulti($(this).hasClass('active'));
  $('.m-footer .multi-select').toggleClass('hide', !$(this).hasClass('active'));
});


//----------------------修改历史----------------------
// 显隐操作历史
$('#op-hint').on('click', function () {
  $(this).toggleClass('active');
  $('.m-panel').toggleClass('hide', !$(this).hasClass('active'));
  setStorage('boxOpHint', $(this).hasClass('active'));
});

// 我的修改痕迹
$('#toggle-my-hint').on('click', function () {
  if (!$.box.isCutMode()) return;
  $(this).toggleClass('active');
  $.page.toggleCurHint('my', currentUserId, !$(this).hasClass('active'));
  $('#hint-list li.active').removeClass('active');
});

// 操作历史-当前状态
$('#hint-list #no-hint').on('click', function () {
  if (!$.box.isCutMode()) return;
  $.page.toggleCurHint(null, null, true);
  $('#toggle-my-hint').removeClass('active');
  $('#hint-list li.active').removeClass('active');
  $(this).addClass('active');
});

// 操作历史-初始状态
$('#hint-list #ini-hint').on('click', function () {
  if (!$.box.isCutMode()) return;
  $.page.toggleCurHint('init');
  $('#toggle-my-hint').removeClass('active');
  $('#hint-list li.active').removeClass('active');
  $(this).addClass('active');
});

// 操作历史-总的修改
$('#hint-list #cmb-hint').on('click', function () {
  if (!$.box.isCutMode()) return;
  $.page.toggleCurHint('comb');
  $('#toggle-my-hint').removeClass('active');
  $('#hint-list li.active').removeClass('active');
  $(this).addClass('active');
});

// 操作历史-某人修改
$(document).on('click', '#hint-list .user-hint', function () {
  if (!$.box.isCutMode()) return;
  $.page.toggleCurHint('user', $(this).attr('title'));
  $('#toggle-my-hint').removeClass('active');
  $('#hint-list li.active').removeClass('active');
  $(this).addClass('active');
});

// 操作历史-某时修改
$(document).on('click', '#hint-list .time-hint', function () {
  if (!$.box.isCutMode()) return;
  $.page.toggleCurHint('time', $(this).attr('title'));
  $('#toggle-my-hint').removeClass('active');
  $('#hint-list li.active').removeClass('active');
  $(this).addClass('active');
});

// 操作历史-播放修改
$('#hint-list #play-hint').on('click', function () {
  if (!$.box.isCutMode()) return;
  if (!$.box.eStatus.times.length)
    return bsShow('提示', '没有修改历史', 'warning', 800);
  $.page.toggleCurBoxType('all', true);
  // $('#op-hint').removeClass('active');
  $('#toggle-my-hint').removeClass('active');
  let play = (i) => {
    let t = $.box.eStatus.times[i];
    bsLoading('', `${t.create_time} @ ${t.username}`);
    $.page.toggleCurHint('time', t.create_time);
  };

  play(0);
  let idx = 1, itv = setInterval(function () {
    if (idx >= $.box.eStatus.times.length) {
      bsHide();
      clearInterval(itv);
      $.page.toggleCurHint(null, null, true);
    } else {
      play(idx++);
    }
  }, 1000);
});

// 操作历史-底部状态栏
$('.m-footer .task-user').on('click', function () {
  $(this).toggleClass('active');
  $.page.toggleCurHint('user', $(this).attr('id'), !$(this).hasClass('active'));
  $('#hint-list li.active').removeClass('active');
  $('#toggle-my-hint').removeClass('active');
});


//----------------------字序操作----------------------
// 更多框序操作
$('#toggle-order-more').on('click', function () {
  if (!$.box.isOrderMode()) return;
  $('#order-op').toggleClass('hide');
});

// 显隐栏框、列框、字框序号
$('.toggle-no').on('click', function () {
  $(this).toggleClass('active');
  let boxType = $(this).attr('id').replace('toggle-no-', '');
  $.page.toggleNo(boxType, $(this).hasClass('active'));
});

// 显隐栏框、列框、字框序线
$('.toggle-link').on('click', function () {
  if (!$.box.isOrderMode()) return;
  $(this).toggleClass('active');
  let boxType = $(this).attr('id').replace('toggle-link-', '');
  $.page.toggleLink(boxType, $(this).hasClass('active'), true);
});

// 算法重新排序
$('#reset-order').on('click', function () {
  if (!$.box.isOrderMode()) return;
  $.box.updateUserLinks();
  $.box.reorderBoxes();
  $.box.drawLink(true);
  bsShow('成功', '已重新排序', 'info', 500);
});

// 加载用户字序
$('#load-user-order').on('click', function () {
  if (!$.box.isOrderMode()) return;
  $.box.updateUserLinks();
  if (!Object.keys($.box.oStatus.userLinks).length)
    return bsShow('提示', '当前无用户字序', 'warning', 800);
  $.box.reorderBoxes();
  $.box.loadUserLinks();
  $.box.drawLink(true);
  bsShow('成功', '已加载用户字序', 'info', 500);
});


//----------------------文本操作----------------------
$('.toggle-txt').on('click', function () {
  $('.toggle-txt').removeClass('active');
  $(this).addClass('active');
  $.box.toggleTxt($(this).attr('id'), true);
});

$('.toggle-v-code').on('click', function () {
  $.box.toggleVCode($(this).attr('id'));
});
