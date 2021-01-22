/**
 * 文字校对
 * Date: 2021-1-21
 */
(function () {
  'use strict';

  $.box.onBoxChanged(function (box, reason, param) {
    if (reason === 'switch') {
      switchCurTxt(box);
    }
  });

  let self = $.box;
  let data = self.data;
  let tStatus = {
    txtHolder: null,                                // 文本所在的页面元素
    curTxtType: 'txt',                              // 当前显示文本类型
    vCodes: [],                                     // 当前文档的异体字
    vCode2norTxt: null,                             // 异体字所属正字
  };

  $.extend($.box, {
    tStatus: tStatus,
    initTxt: initTxt,
    toggleTxt: toggleTxt,
    hasTxtType: hasTxtType,
    toggleVCode: toggleVCode,
  });

  function initTxt(txtHolder, txtType, useToolTip) {
    let boxes = self.getBoxes();
    if (!boxes.blocks.length) return;
    let html = '', blockNo = null, columnNo = null;
    let lastBlockNo = boxes.blocks[boxes.blocks.length - 1]['block_no'];
    let lastColumnNo = boxes.columns[boxes.columns.length - 1]['column_no'];
    boxes.chars.forEach((b) => {
      // init
      b['txt'] = b['txt'] || b['ocr_txt'] || '■';
      b['ocr_chr'] = b['alternatives'] && Array.from(b['alternatives'])[0];
      if (b['txt'].indexOf('v') === 0) tStatus.vCodes.push(b['txt']);
      // html
      if (blockNo !== b.block_no) {
        html += (!blockNo ? '</div></div>' : '') + '<div class="block"><div class="line">';
        blockNo = b.block_no;
        columnNo = 1;
      } else if (columnNo !== b.column_no) {
        html += '</div><div class="line">';
        columnNo = b.column_no;
      }
      let attr = getTxtAttr(b), tip = '';
      if (useToolTip && attr.cls.replace('char', '').length > 1) {
        let toward = (b.block_no === lastBlockNo && b.column_no > 3 && b.column_no > lastColumnNo - 3) ? 'top' : 'bottom';
        tip = `data-toggle="tooltip" data-html="true" data-placement="${toward}" title="${attr.tip}"`;
      }
      html += `<span id="idx-${b.idx}" class="${attr.cls}" ${tip}>${getHtml(b, txtType)}</span>`;
    });
    html += '</div></div>';
    $(txtHolder).html(html);
    tStatus.txtHolder = txtHolder;
    if (useToolTip) $('[data-toggle="tooltip"]').tooltip();
    if (tStatus.vCodes.length) $('#toggle-v-code').removeClass('hide');
  }

  function getHtml(box, txtType) {
    let html = box[txtType] || '■';
    if (txtType === 'nor_txt') html = box['txt'];
    if (txtType === 'txt' && html.indexOf('v') === 0)
      html = `<img src="/static/img/variants/${html}.jpg">`;
    if (txtType === 'nor_txt' && html.indexOf('v') === 0) {
      html = tStatus.vCode2norTxt[html] || html;
    }
    return html;
  }

  function getTxtAttr(box) {
    let txts = [], cls = 'char', tips = [];
    if (box['txt']) {
      tips.push(`校对文本: ${box['txt']}`);
    }
    if (box['ocr_txt']) {
      txts.push(box['ocr_txt']);
      tips.push(`综合OCR: ${box['ocr_txt']}`);
    }
    if (box['alternatives']) {
      let chr_txt = Array.from(box['alternatives'])[0];
      txts.push(chr_txt);
      tips.push(`字框OCR: ${chr_txt}`);
    }
    if (box['ocr_col']) {
      txts.push(box['ocr_col']);
      tips.push(`列框OCR: ${box['ocr_col']}`);
    }
    if (box['cmp_txt']) {
      txts.push(box['cmp_txt']);
      tips.push(`比对文本: ${box['cmp_txt']}`);
    }
    txts = txts.filter((t) => t !== '■');
    if (txts.length > 1 && new Set(txts).size > 1) cls += ' is-diff';
    if (box['txt'] && box['txt'].indexOf('v') === 0) cls += ' v-code';
    if (box['txt'] && box['txt'] !== '■' && (txts.indexOf(box['txt']) < 0 || box['txt_logs']))
      cls += ' changed';
    return {cls: cls, tip: tips.join('<br>')};
  }

  function toggleTxt(txtType, show) {
    if (!tStatus.txtHolder || tStatus.curTxtType === txtType) return;
    if (txtType && show) {
      tStatus.curTxtType = txtType;
      if (txtType === 'nor_txt' && tStatus.vCodes.length && !tStatus.vCode2norTxt) {
        postApi('/variant/code2nor', {data: {codes: tStatus.vCodes}}, function (res) {
          tStatus.vCode2norTxt = res['code2nor'] || {};
          showTxt(txtType);
        });
      } else {
        showTxt(txtType)
      }
    }
  }

  function showTxt(txtType) {
    $.map($(tStatus.txtHolder).find('.char'), function (item) {
      let idx = $(item).attr('id').split('-')[1];
      $(item).html(getHtml(data.boxes[idx], txtType));
    })
  }

  function toggleVCode(show) {
    if (tStatus.curTxtType !== 'txt') return;
    $.map($(tStatus.txtHolder).find('.char.v-code'), function (item) {
      if (show && $(item).text().trim().indexOf('v') === 0)
        $(item).html(`<img src="/static/img/variants/${$(item).text().trim()}.jpg">`);
      if (!show && $(item).find('img').length)
        $(item).text($(item).find('img').attr('src').split('/').pop().replace('.jpg', ''));
    })
  }

  function switchCurTxt(box) {
    if (!tStatus.txtHolder) return;
    let holder = $(tStatus.txtHolder);
    holder.find('.current-txt').removeClass('current-txt');
    if (box && box.boxType === 'char') {
      let $this = holder.find('#idx-' + box.idx);
      $('.current-char').removeClass('current-char');
      $this.addClass('current-char');
      $('.current-line').removeClass('current-line');
      $this.parent().addClass('current-line');
      let hp = $(tStatus.txtHolder).offset(), cp = $this.offset();
      if ((cp.top - hp.top > holder.height() + holder.scrollTop()) || (cp.top < hp.top)) {
        holder.animate({scrollTop: cp.top - hp.top - 10}, 500);
      }
    }
  }

  function hasTxtType(txtType) {
    let chars = self.getBoxes()['chars'];
    if (chars.length === 1 && txtType in chars[0]) return true;
    return chars.length >= 2 && txtType in chars[0] && txtType in chars[1];
  }

  $(document).on('click', '.txt-holder .char', function (e) {
    let idx = $(this).attr('id').split('-')[1];
    self.switchCurBox(data.boxes[idx]);
  });

}());