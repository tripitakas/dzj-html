/**
 @desc 切分相关操作
 */

// 检查框外框，并重新排序
$('#btn-check-cut').on('click', function () {
  let r = $.box.checkBoxes();
  if (r.status) {
    if ($.box.cStatus.hasChanged) $.box.reorderBoxes();
    bsShow('成功', '检查无误!', 'info', 1500);
  }
});

// 检查序线，并更新序号
$('#btn-check-link').on('click', function () {
  let r = $.box.checkLinks();
  if (!r.status) {
    $.page.toggleLink(r.errorBoxType, true);
  } else {
    if ($.box.oStatus.hasChanged) $.box.updateNoByLinks(r.links);
    bsShow('成功', '检查无误', 'info', 1500);
  }
});

// 切换切分校对、字序校对模式
$('.toggle-mode').on('click', function () {
  $.page.toggleMode($(this).attr('id').replace('toggle-', ''));
});

// 我的修改痕迹
$('#toggle-my-hint').on('click', function () {
  $(this).toggleClass('active');
  $.page.toggleMyHint(currentUserId, $(this).hasClass('active'));
});

// 操作历史-当前状态
$('#hint-list #no-hint').on('click', function () {
  $.box.hideAllHint();
});

// 操作历史-初始状态
$('#hint-list #ini-hint').on('click', function () {
  $.page.toggleHint('ini');
});

// 操作历史-总的修改
$('#hint-list #cmb-hint').on('click', function () {
  $.page.toggleHint('cmb');
});

// 操作历史-播放
$('#hint-list #play-hint').on('click', function () {
  if (!$.box.eStatus.times.length)
    return showTips('提示', '没有修改历史', 1000);
  !$('#toggle-all').hasClass('active') && $('#toggle-all').click();
  $('#op-hint').removeClass('open');
  let play = (i) => {
    let t = $.box.eStatus.times[i];
    bsLoading('', `${t.create_time} @ ${t.username}`);
    $.page.toggleHint('time', t.create_time);
  };

  play(0);
  let idx = 1, itv = setInterval(function () {
    if (idx >= $.box.eStatus.times.length) {
      clearInterval(itv);
      bsHide();
      $.box.hideAllHint();
      $.page.updateFootHintNo();
    } else {
      play(idx++);
    }
  }, 2000);
});

// 切换蒙白、透视、大小窄扁、重叠等属性
$('.toggle-shape').on('click', function () {
  $(this).toggleClass('active');
  $.page.toggleCurShape($(this).attr('id').replace('toggle-', ''), $(this).hasClass('active'));
});

// 算法重新排序
$('#reset-order').on('click', function () {
  $.box.updateUserLinks();
  $.box.reorderBoxes();
  $.box.drawLink(true);
});

// 加载用户字序
$('#load-user-order').on('click', function () {
  $.box.updateUserLinks();
  $.box.reorderBoxes();
  $.box.loadUserLinks();
  $.box.drawLink(true);
});

// 更多框操作
$('#toggle-box-more').on('click', function () {
  $('#box-op').toggleClass('hide');
});

// 显隐栏框、列框、字框、所有
$('.toggle-box').on('click', function () {
  $(this).toggleClass('active');
  $.page.toggleCurBoxType($(this).attr('id').replace('toggle-', ''), $(this).hasClass('active'));
});

// 更多框序操作
$('#toggle-order-more').on('click', function () {
  $('#order-op').toggleClass('hide');
});

// 显隐底框
$('#toggle-back-box').on('click', function () {
  $(this).toggleClass('active');
  $.page.toggleBackBox($(this).hasClass('active'));
});

// 显隐栏框、列框、字框序号
$('.toggle-no').on('click', function () {
  $(this).toggleClass('active');
  let boxType = $(this).attr('id').replace('toggle-no-', '');
  $.page.toggleNo(boxType, $(this).hasClass('active'));
});

// 显隐栏框、列框、字框序线
$('.toggle-link').on('click', function () {
  $(this).toggleClass('active');
  let boxType = $(this).attr('id').replace('toggle-link-', '');
  $.page.toggleLink(boxType, $(this).hasClass('active'), true);
});

// 显隐左侧
$('#toggle-left').on('click', function () {
  $(this).toggleClass('active');
  $('#left-region').toggleClass('hide', $(this).hasClass('active'));
});

// 隐藏右侧
$('#toggle-right').on('click', function () {
  $(this).toggleClass('active');
  $('#right-region').toggleClass('hide', !$(this).hasClass('active'));
});

// 显隐图片
$('#toggle-image').on('click', function () {
  $(this).toggleClass('active');
  $.box.toggleImage($('#toggle-image').hasClass('active'));
  let key = $(this).parent().hasClass('order') ? 'toggleOrderImage' : 'toggleCutImage';
  setStorage(key, $(this).hasClass('active') ? '1' : '-1');
});

// 模糊图片
$('#toggle-blur').on('click', function () {
  $(this).toggleClass('active');
  $.box.setImageOpacity($(this).hasClass('active') ? 0.2 : 1);
  let key = $(this).parent().hasClass('order') ? 'blurOrderImage' : 'blurCutImage';
  setStorage(key, $(this).hasClass('active') ? '1' : '-1');
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

// 撤销
$('#undo').on('click', function () {
  $.box.undo();
});

// 重做
$('#redo').on('click', function () {
  $.box.redo();
});

// 多选模式
$('#toggle-multi').on('click', function () {
  $(this).toggleClass('active');
  $.box.toggleMulti($(this).hasClass('active'));
  bsShow('', '多选模式已' + ($(this).hasClass('active') ? '开启' : '关闭'), 'info', 800);
});

// 查看page
$('.m-footer .page-name').on('click', function () {
  if ($(this).hasClass('disabled')) return;
  let url = '/tptk/' + $(this).text();
  let charName = $('.m-footer .char-name').text();
  if (typeof charName !== 'undefined' && charName !== '' && charName !== '未选中') {
    let cid = charName.split('_').pop();
    cid = cid.split('#').pop();
    url += '?cid=' + cid;
  }
  window.open(url, '_blank');
});

// 查看char
$('.m-footer .char-name').on('click', function () {
  let charName = $(this).text();
  if ($(this).hasClass('disabled') || charName === '未选中') return;
  if (!/b\dc\d+c\d+/.test(charName))
    return showTips('提示', '当前不是字框，无法查看', 3000);
  if (charName.indexOf('#') > -1) {
    let cid = charName.split('#').pop();
    let pageName = $('.m-footer .page-name').text();
    charName = pageName + '_' + cid;
  }
  window.open('/char/' + charName, '_blank');
});

