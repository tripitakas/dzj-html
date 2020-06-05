/** 导航相关*/
// 排序
$('#btn-cc-up').on('click', () => location.href = setQueryString('order', 'cc'));
$('#btn-cc-down').on('click', () => location.href = setQueryString('order', '-cc'));

// 过滤
$('#btn-my-update').on('click', () => location.href = setQueryString('update', 'my'));
$('#btn-all-update').on('click', () => location.href = setQueryString('update', 'all'));
$('#btn-submitted').on('click', () => location.href = setQueryString('submitted', 'true'));
$('#btn-not-submitted').on('click', () => location.href = setQueryString('submitted', 'false'));
$('#btn-diff').on('click', () => location.href = setQueryString('diff', 'true'));

// 按置信度过滤
$('#btn-filter').on('click', function () {
  var start = $('#filter-start').val();
  if (start && start.match(/^(0\.\d+|0|1|1\.0)$/) === null)
    return showWarning('提示', '起始值不符合要求');
  var end = $('#filter-end').val();
  if (end && end.match(/^(0\.\d+|0|1|1\.0)$/) === null)
    return showWarning('提示', '终止值不符合要求');
  if (!start.length && !end.length)
    return showWarning('提示', '请输入起始值或终止值');
  if (start.length && !end.length) {
    location.href = setQueryString('cc', '>=' + start);
  } else if (end.length && !start.length) {
    location.href = setQueryString('cc', '<=' + end);
  } else {
    location.href = setQueryString('cc', start + ',' + end);
  }
});

// 全部选择
$('#bat-select').on('click', function () {
  $(this).toggleClass('active');
  if ($(this).hasClass('active')) {
    $('.char-check :checkbox').prop('checked', true);
  } else {
    $('.char-check :checkbox').removeAttr('checked');
  }
});

// 检索异体字
$('#search-variant').on('keydown', function (event) {
  var keyCode = event.keyCode || event.which;
  if (keyCode === 13) {
    var q = $(this).val().trim();
    if (q.length)
      window.open('http://hanzi.lqdzj.cn/variant_search?q=' + q, '_blank');
  }
});
$('#icon-search').on('click', function () {
  var q = $('#search-variant').val().trim();
  if (q.length)
    window.open('http://hanzi.lqdzj.cn/variant_search?q=' + q, '_blank');
});

// 显隐字图信息
$('#toggle-char-info').on('click', function () {
  $(this).toggleClass('active');
  setStorage('toggle-char-info', $(this).hasClass('active'));
  $('.char-info, .cc').toggleClass('hide', !$(this).hasClass('active'));
});

// 显隐中间列图
$('#toggle-column-panel').on('click', function () {
  $(this).toggleClass('active');
  setStorage('toggle-column-panel', $(this).hasClass('active'));
  $('.column-panel').toggleClass('hide', !$(this).hasClass('active'));
});

// 显隐右侧工作面板
$('#toggle-work-panel').on('click', function () {
  $(this).toggleClass('active');
  setStorage('toggle-work-panel', $(this).hasClass('active'));
  $('.work-panel').toggleClass('hide', !$(this).hasClass('active'));
});

/** 左侧字图列表 */
// 切换字种
$('.txt-kind').on('click', function () {
  var txt = $(this).attr('data-value') || $(this).text().trim();
  location.href = txt ? setQueryString('txt', txt) : location.pathname;
});

// 单击字图
$('.char-panel .char-img').on('click', function () {
  $('.char-items .current').removeClass('current');
  $(this).parent().addClass('current');
  var id = $(this).parent().attr('data-id');
  var ch = chars[id] || {};
  updateColumnImg(ch);
  updateCharTxtPanel(ch);
});

$('.char-panel .char-info, .char-panel .char-check').on('click', function () {
  $(this).parent().find(':checkbox').click();
});

$('.char-check input').on('click', function (e) {
  e.stopPropagation();
});

/** 中间列图面板 */
// 更新列图
var paper, charBox, getBox;

function updateColumnImg(ch) {
  var column = ch.column; // 列框
  var columnImg = $('#col-holder'); // 列框容器DIV
  var ratio = Math.min(columnImg.height() / column.h, 108 / column.w);  // 列图显示比例
  var imgName = ch['page_name'] + '_' + ch.column.cid;  // 列图文件名
  var imgPath = 'columns/' + imgName.split('_').slice(0, -1).join('/') + '/' + imgName + '_' + ch.column.hash + '.jpg';
  var columnUrl = columnBaseUrl.replace(/columns\/.*?.jpg/, imgPath); // 列图URL

  if ($.cut) {
    $.cut.create({
      addDisable: true,
      holder: 'col-holder',
      image: columnUrl,
      width: column.w,
      height: column.h,
      name: imgName,
      chars: [{x: ch.pos.x - column.x, y: ch.pos.y - column.y, w: ch.pos.w, h: ch.pos.h}]
    });
    $.cut.bindKeys();
    getBox = function () {
      var c = $.cut.exportBoxes()[0];
      ch._boxChanged = ch._boxChanged ||
          Math.abs(c.x + column.x - ch.pos.x) > 1 || Math.abs(c.y + column.y - ch.pos.y) > 1 ||
          Math.abs(ch.pos.w - c.w) > 1 || Math.abs(ch.pos.h - c.h) > 1;
      ch.pos.x = c.x + column.x;
      ch.pos.y = c.y + column.y;
      ch.pos.w = c.w;
      ch.pos.h = c.h;
      return ch;
    };
    return;
  }

  charBox && charBox.remove();
  charBox = null;
  if (imgName !== columnImg.attr('data-id')) {  // 列图改变则重新创建，否则只更新字框
    columnImg.attr('data-id', imgName);
    paper && paper.remove();
    paper = Raphael('col-holder', column.w + 8, column.h + 8).initZoom(); // 创建稍大的画板，以便字框部分出界看不见
    paper.image(columnUrl, 4, 4, column.w, column.h).initZoom();
    charBox = paper.rect(ch.pos.x - column.x + 4, ch.pos.y - column.y + 4, ch.pos.w, ch.pos.h).initZoom()
        .setAttr({stroke: '#158815', 'stroke-width': 0, fill: 'rgba(255, 0, 0, .4)'});
    paper.setZoom(ratio).setSize((column.w + 8) * ratio, (column.h + 8) * ratio);
  } else if (paper) {
    charBox = paper.rect(ch.pos.x - column.x + 4, ch.pos.y - column.y + 4, ch.pos.w, ch.pos.h).initZoom(1)
        .setAttr({stroke: '#158815', 'stroke-width': 0, fill: 'rgba(255, 0, 0, .4)'}).setZoom(ratio);
  }
}

// 提交字框修改
$('#submit-box').on('click', function () {
  var name = $('.char-edit .current-name').val();
  var data = {'pos': getBox()['pos'], 'task_type': taskType};
  postApi('/char/box/' + name, {data: data}, function (res) {
    bsShow('成功！', '已保存成功', 'success', 1000);
    updateBoxLogs(res.box_logs);
  });
});