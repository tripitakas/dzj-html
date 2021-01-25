/**
 * 单字校对
 * Date: 2021-1-10
 */
(function () {
  'use strict';

  $.box.onBoxChanged(function (box, reason, param) {
    if (reason === 'switch') {
      if ($.box.tStatus && box && box.boxType === 'char') {
        $.charTxt.setChar(box);
      }
    }
  });

  let status = {
    readonly: true,           // 是否只读
    showBase: true,           // 是否显示字符基本信息
    showTxtLogs: true,        // 是否显示文字校对历史
    showBoxLogs: true,        // 是否显示切分校对历史
    char: null,               // 当前校对字符数据
    hint: null,               // 当前显示修改痕迹
  };

  $.charTxt = {
    status: status,
    init: init,
    setChar: setChar,
    setTxtLogs: setTxtLogs,
    setBoxLogs: setBoxLogs,
    toggleHint: toggleHint,
  };

  function init(p) {
    if ('showBase' in p) status.showBase = p.showBase;
    if ('showTxtLogs' in p) status.showTxtLogs = p.showTxtLogs;
    if ('showBoxLogs' in p) status.showBoxLogs = p.showBoxLogs;
    if (p.char) setChar(p.char);
    if ('readonly' in p) status.readonly = p.readonly;
    $('.user-panel .btn-submit').toggleClass('unauthorized', status.readonly);
  }

  function setChar(char) {
    setBaseInfo(char);
    setAlternatives(char);
    setTxtLogs(char['txt_logs']);
    setBoxLogs(char['box_logs']);
    setUserPanel(char);
    setPageParams(char);
    status.char = char;
  }

  function isValid(txt) {
    return txt && txt !== '■';
  }

  function setBaseInfo(char) {
    $('#base-info').toggleClass('hide', !status.showBase);
    if (!status.showBase) return;
    let fields = {
      'name': '字编码', 'char_id': '序号', 'source': '分类', 'cc': '置信度', 'sc': '相似度', 'pos': '坐标',
      'column': '所属列', 'is_diff': '是否不一致', 'un_required': '是否不必校对', 'txt': '原字',
      'nor_txt': '正字', 'is_vague': '笔画残损', 'is_deform': '异形字', 'uncertain': '不确定',
      'box_level': '切分等级', 'box_point': '切分积分',
      'txt_level': '文字等级', 'txt_point': '文字积分',
      'remark': '备注'
    };
    $('#base-info .meta').html(Object.keys(fields).map((f) => {
      if (!char[f]) return '';
      if (['pos', 'column'].indexOf(f) > -1) {
        let info = JSON.stringify(char[f]).replace(/["{}]/g, '');
        return `<label>${fields[f]}</label><span class="pos">${info}</span><br/>`;
      } else {
        return `<label>${fields[f]}</label><span>${char[f]}</span><br/>`;
      }
    }).join(''));
  }

  function setAlternatives(char) {
    let html = isValid(char['ocr_col']) ? `<span class="txt-item ocr-col${char['ocr_col'] === char.txt ? ' active' : ''}">${char['ocr_col']}</span>` : '';
    html += isValid(char['cmp_txt']) ? `<span class="txt-item cmp-txt${char['cmp_txt'] === char.txt ? ' active' : ''}">${char['cmp_txt']}</span>` : '';
    html += Array.from(char['alternatives'] || '').map(function (c, n) {
      return `<span class="txt-item${n ? '' : ' ocr-char'}${c === char.txt ? ' active' : ''}">${c}</span>`;
    }).join('');
    $('#txt-alternatives .body').html(html);
    $('#txt-alternatives .body').toggleClass('hide', !html.length);
  }

  function setTxtLogs(txtLogs) {
    $('#txt-logs').toggleClass('hide', !status.showTxtLogs);
    if (!status.showTxtLogs) return;
    let html = (txtLogs || []).map(function (log) {
      let meta = log.txt ? `<label>校对文字</label><span>${log.txt}</span><br/>` : '';
      meta += log.is_deform ? `<label>异形字</label><span>是</span><br/>` : '';
      meta += log.is_vague ? `<label>笔画残损</label><span>是</span><br/>` : '';
      meta += log.uncertain ? `<label>不确定</label><span>是</span><br/>` : '';
      meta += log.remark ? `<label>备注</label><span>${log.remark}</span><br/>` : '';
      meta += log.username ? `<label>校对人</label><span>${log.username}</span><br/>` : '';
      meta += log.create_time ? `<label>创建时间</label><span>${toLocalTime(log.create_time)}</span><br/>` : '';
      meta += log.updated_time ? `<label>更新时间</label><span>${toLocalTime(log.updated_time)}</span><br/>` : '';
      return `<div class="log meta">${meta}</div>`;
    }).join('');
    $('#txt-logs .body').html(html);
    $('#txt-logs').toggleClass('hide', !html.length);
  }

  function setBoxLogs(boxLogs) {
    $('#box-logs').toggleClass('hide', !status.showTxtLogs);
    if (!status.showBoxLogs) return;
    let html = (boxLogs || []).map(function (log) {
      let t = {initial: '初始', added: '新增', deleted: '删除', changed: '修改'};
      let meta = log.op ? `<label>操作</label><span>${t[log.op]}</span><br/>` : '';
      if (log.pos || log.x) {
        let pos = ['x', 'y', 'w', 'h'].map((p) => (log.pos ? log.pos[p] : log[p]) || '0').join('/');
        meta += `<label>坐标</label><span class="pos">${pos}</span><br/>`;
      }
      meta += log.username ? `<label>校对人</label><span>${log.username}</span><br/>` : '';
      meta += log.create_time ? `<label>创建时间</label><span>${toLocalTime(log.create_time)}</span><br/>` : '';
      meta += log.updated_time ? `<label>更新时间</label><span>${toLocalTime(log.updated_time)}</span><br/>` : '';
      return `<div class="log meta">${meta}</div>`;
    }).join('');
    $('#box-logs .body').html(html);
    $('#box-logs').toggleClass('hide', !html.length);
  }

  function setUserPanel(char) {
    $('#p-remark').val(char.remark || '');
    $('#p-txt').val(char.txt || char['ocr_txt']);
    let val1 = char['is_vague'] ? '1' : '0';
    $('.is-vague :radio').map(function (i, item) {
      ($(item).val() === val1) ? $(item).prop('checked', true) : $(item).removeAttr('checked');
    });
    let val2 = char['is_deform'] ? '1' : '0';
    $('.is-deform :radio').map(function (i, item) {
      ($(item).val() === val2) ? $(item).prop('checked', true) : $(item).removeAttr('checked');
    });
    let val3 = char['uncertain'] ? '1' : '0';
    $('.uncertain :radio').map(function (i, item) {
      ($(item).val() === val3) ? $(item).prop('checked', true) : $(item).removeAttr('checked');
    });
    if (status.readonly) $('.proof .btn-submit').addClass('hide');
  }

  function setPageParams(char) {
    let pageName = $('.m-footer .page-name').text();
    $('#search-variant').val(char.txt || char['ocr_txt']);
    if (char.name) $('.m-footer .char-name').text(char.name);
    if (char.page_name) $('.m-footer .page-name').text(char.page_name);
    $('.char-txt .cur-name').val(char.name || pageName + '_' + char.cid);
  }

  // 显隐box对应的框
  function toggleHint(box, show) {
    status.hint && status.hint.remove();
    status.hint = null;
    if (!show) {
      $($.box.data.holder).removeClass('show-hint user-hint');
    } else if (box) {
      $($.box.data.holder).addClass('show-hint user-hint');
      status.hint = $.box.createBox(box, 'box hint current');
    }
  }

  // 选中文字
  $(document).on('click', '.txt-item', function () {
    let txt = $(this).attr('data-value') || $(this).text().trim();
    $('.proof #p-txt').val(txt);
    $('.txt-item').map(function (i, item) {
      let txt2 = $(item).attr('data-value') || $(item).text();
      $(item).toggleClass('active', txt2 === txt);
    });
  });

  // 展开收缩信息
  $(document).on('click', '.toggle-info', function () {
    let target = $(this).attr('id').replace('toggle-', '');
    if ($(this).hasClass('icon-up')) {
      $(this).removeClass('icon-up').addClass('icon-down');
      $(`#${target} .body`).addClass('hide');
    } else if ($(this).hasClass('icon-down')) {
      $(this).removeClass('icon-down').addClass('icon-up');
      $(`#${target} .body`).removeClass('hide');
    }
  });

  // 显示坐标对应的框
  $(document).on('click', 'span.pos', function () {
    let txt = $(this).text(), box = {x: 0, y: 0, w: 0, h: 0, cid: 0};
    if (txt.split(',').length > 3) {
      txt.split(',').forEach((item) => {
        let a = item.split(':');
        if (a.length === 2) box[a[0]] = parseInt(a[1]);
      });
    } else if (txt.split('/').length > 3) {
      let a = txt.split('/');
      box = {x: parseInt(a[0]), y: parseInt(a[1]), w: parseInt(a[2]), h: parseInt(a[3]), cid: 0};
    }
    box.boxType = box.cid ? 'column' : 'char';
    toggleHint(box, true);
    $('#reset-box').removeClass('hide');
  });


}());