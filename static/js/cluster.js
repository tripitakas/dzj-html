/**
 * 聚类校对
 * Date: 2021-1-23
 */
(function () {
  'use strict';

  let status = {
    chars: [],                                      // 字数据
    txtKinds: [],                                   // 校对字头
    curTxt: '',                                     // 当前字头
    variants: [],                                   // 当前字头的异体字列表
    colHolder: null,                                // 画布所在的页面元素
    curChar: null,                                  // 当前框
    curColImgUrl: null,                             // 当前列框url
  };

  $.cluster = {
    status: status,
    init: init,
    addVariant: addVariant,
    updateChar: updateChar,
    switchCurChar: switchCurChar,
    exportSubmitData: exportSubmitData,
  };

  function init(p) {
    // 先设置curTxt，后设置txtKinds和variants
    if (p.curTxt) status.curTxt = p.curTxt;
    if (p.txtKinds) setTxtKinds(p.txtKinds);
    if (p.variants) setVariants(p.variants);
    // chars、colHolder
    if (p.chars) setChars(p.chars);
    if (p.colHolder) status.colHolder = p.colHolder;
    // $.box
    $.box.status.readonly = false;
    $.box.status.curBoxType = 'char';
  }

  function exportSubmitData() {
    let chars = $.box.exportSubmitData()['op']['chars'];
    let char = chars && chars[0];
    if (!char || char.op !== 'changed') return bsShow('', '字框未发生修改', 'warning', 1000);
    char['name'] = status.curChar['name'];
    char['x'] += status.curChar['column']['x'];
    char['y'] += status.curChar['column']['y'];
    return char;
  }

  function setTxtKinds(txtKinds) {
    status.txtKinds = txtKinds;
    let html = txtKinds.map((item) => {
      let cls = item === status.curTxt ? ' current' : '';
      if (item.indexOf('v') === 0 && item.length > 1)
        return `<span class="txt-kind img-kind${cls}" data-value="${item}"><img src="/static/img/variants/${item}.jpg"/></span>`;
      else
        return `<span class="txt-kind${cls}">${item}</span>`;
    }).join('');
    $('.char-panel .txt-kinds').html('<span class="txt-kind reset"></span>' + html);
  }

  function setVariants(variants) {
    if (!status.curTxt.length) return $('.char-panel .variants').addClass('hide');
    let html = variants.map((item) => {
      if (item.indexOf('v') === 0 && item.length > 1)
        return `<span class="variant txt-item" data-value="${item}"><img src="/static/img/variants/${item}.jpg"/></span>`;
      else
        return `<span class="variant txt-item">${item}</span>`;
    }).join('');
    $('.char-panel .variants').html('<span id="add-variant" class="variant">+</span>' + html);
    status.variants = variants;
  }

  function addVariant(item) {
    let html = `<span class="variant txt-item">${item}</span>`;
    if (item.indexOf('v') === 0 && item.length > 1)
      html = `<span class="variant txt-item" data-value="${item}"><img src="/static/img/variants/${item}.jpg"/></span>`;
    $('.char-panel .variants').append(html);
  }

  function setChars(chars) {
    status.chars = chars;
    let taskId = typeof gTaskId === 'undefined' ? '' : gTaskId;
    let taskType = typeof gTaskType === 'undefined' ? '' : gTaskType;
    let html = chars.map((ch, i) => {
      let cls = ch['is_diff'] ? 'is-diff' : '';
      cls += ch['un_required'] ? ' un-required' : '';
      cls += ch['txt'] !== ch['ocr_txt'] ? ' changed' : '';
      let tasks = ch['tasks'] && ch['tasks'][taskType] || [];
      return [
        `<div class="char-item ${cls.trim()}" id="${ch.name}" data-value="${i}">`,
        `<div class="char-img"><img src="${ch['img_url']}"/></div>`,
        `<div class="char-info"><span class="txt">${ch['txt'] || ch['ocr_txt']}</span>`,
        `<span class="submitted${tasks.indexOf(taskId) > -1 ? '' : ' hide'}"><i class="icon-check"></i></span></div>`,
        `<div class="char-check"><span class="cc">${(ch['cc'] || 0) / 1000}</span><input type="checkbox"></div>`,
        `</div>`,
      ].join('');
    }).join('');
    $('.char-panel .char-items').html(html);
  }

  function switchCurChar(ch) {
    // 更新列图
    let col = ch['column'];
    if (status.curColImgUrl !== col['img_url']) {
      status.curColImgUrl = col['img_url'];
      $.box.initSvg(status.colHolder, status.curColImgUrl, col.w, col.h, 'width-full');
      $.box.bindCut({onlyChange: true});
    }
    // 更新字框
    $.box.setBoxes({chars: [{x: ch.pos.x - col.x, y: ch.pos.y - col.y, w: ch.pos.w, h: ch.pos.h}]}, true);
    $.box.switchCurBox($.box.data.boxes[0]);
    status.curChar = ch;
  }

  function updateChar(charName, info) {
    for (let i = 0, len = status.chars.length; i < len; i++) {
      let ch = status.chars[i];
      if (ch.name === charName) {
        Object.assign(ch, info);
        return;
      }
    }
  }

}());