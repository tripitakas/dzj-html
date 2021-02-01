/**
 * 聚类校对
 * Date: 2021-1-23
 */
(function () {
  'use strict';

  let status = {
    chars: [],                                      // 字数据
    curTxt: '',                                     // 当前字头
    txtKinds: [],                                   // 校对字头
    txt2Variants: {},                               // 校对字头的异体字
    colHolder: null,                                // 列图画布的页面元素
    curChar: null,                                  // 当前字框
    curColImgUrl: null,                             // 当前列图的url
  };

  $.cluster = {
    status: status,
    init: init,
    setChars: setChars,
    addVariant: addVariant,
    setVariants: setVariants,
    loadVariants: loadVariants,
    addTxtKind: addTxtKind,
    setTxtKinds: setTxtKinds,
    updateChar: updateChar,
    updatePager: updatePager,
    switchCurChar: switchCurChar,
    exportSubmitData: exportSubmitData,
  };

  function init(p) {
    // 先设置curTxt，后设置txtKinds和variants
    if (p.curTxt) status.curTxt = p.curTxt;
    if (p.txtKinds) setTxtKinds(p.txtKinds);
    if (p.variants) setVariants(p.variants);
    toggleVariants(p.curTxt && p.curTxt.length);
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
    if (txtKinds.length === status.txtKinds.length &&
        !txtKinds.filter((t) => status.txtKinds.indexOf(t) < 0).length) return;
    let html = txtKinds.map((item) => {
      let cls = item === status.curTxt ? ' current' : '';
      let html = `<span class="txt-kind${cls}">${item}</span>`;
      if (item.indexOf('v') === 0 && item.length > 1)
        html = `<span class="txt-kind img-kind${cls}" data-value="${item}"><img src="/static/img/variants/${item}.jpg"/></span>`;
      return html;
    }).join('');
    $('.char-panel .txt-kinds').html('<span class="txt-kind reset"></span>' + html);
    status.txtKinds = txtKinds;
  }

  function addTxtKind(item) {
    if (status.txtKinds.indexOf(item) > -1) return;
    let cls = item === status.curTxt ? ' current' : '';
    let html = `<span class="txt-kind${cls}">${item}</span>`;
    if (item.indexOf('v') === 0 && item.length > 1)
      html = `<span class="variant txt-item" data-value="${item}"><img src="/static/img/variants/${item}.jpg"/></span>`;
    $('.char-panel .txt-kinds').append(html);
    status.txtKinds.push(item);
  }

  function toggleVariants(show) {
    $('.char-panel .variants').toggleClass('hide', !show);
  }

  function setVariants(txt, variants, append) {
    let html = variants.map((item) => {
      let cls = `variant txt-item${append ? ' v-append' : ''}`;
      if (item.indexOf('v') === 0 && item.length > 1)
        return `<span class="${cls}" data-value="${item}"><img src="/static/img/variants/${item}.jpg"/></span>`;
      else
        return `<span class="${cls}">${item}</span>`;
    }).join('');
    if (append) {
      if (!variants.length) {
        bsShow('提示', '查无异体字', 'info', 1000);
      } else {
        $('.char-panel .variants .v-append').remove();
        $('.char-panel .variants').append('<span class="v-append v-first"></span>' + html);
      }
    } else {
      $('.char-panel .variants').html('<span id="add-variant" class="variant">+</span>' + html);
    }
    status.txt2Variants[txt] = variants;
  }

  function addVariant(item) {
    let variants = status.txt2Variants[status.curTxt] || [];
    if (variants.indexOf(item) > -1) return;
    let html = `<span class="variant txt-item">${item}</span>`;
    if (item.indexOf('v') === 0 && item.length > 1)
      html = `<span class="variant txt-item" data-value="${item}"><img src="/static/img/variants/${item}.jpg"/></span>`;
    $('.char-panel .variants').append(html);
    status.txt2Variants[status.curTxt].push(item);
  }

  function loadVariants(txt, append) {
    if (!txt.length) return;
    for (let t in status.txt2Variants) {
      let vts = status.txt2Variants[t];
      if (txt === t || vts.indexOf(txt) > -1) return setVariants(txt, vts, append);
    }
    postApi('/variant/search', {data: {q: txt}}, function (res) {
      status.txt2Variants[txt] = res.variants;
      setVariants(txt, res.variants, append);
    });
  }

  function setChars(chars) {
    status.chars = chars;
    let taskId = typeof gTaskId === 'undefined' ? '' : gTaskId;
    let taskType = typeof gTaskType === 'undefined' ? '' : gTaskType;
    let getCc = (cc) => Math.round((cc > 1 ? cc / 1000 : cc) * 100) / 100;
    let html = chars.map((ch, i) => {
      let tasks = ch['tasks'] && ch['tasks'][taskType] || [];
      tasks = tasks.map((t) => t['$oid'] || t);
      let cls = tasks.indexOf(taskId) > -1 ? ' submitted' : '';
      cls += (ch['txt'] && ch['txt'] !== (ch['cmb_txt'] || ch['ocr_txt'])) ? ' changed' : '';
      cls += ch['sc'] ? ` sc-${ch['sc']}` : '';
      return [
        `<div class="char-item${cls}" id="${ch.name}" data-value="${i}">`,
        `<div class="char-img"><img src="${ch['img_url']}"/></div>`,
        `<div class="char-info"><span class="cc">${getCc(ch['cc'] || 0)}</span>|<span class="lc">${getCc(ch['lc'] || 0)}</span></div>`,
        `<div class="char-check"><span class="txt">${ch['txt'] || ch['cmb_txt']}</span><input type="checkbox"></div>`,
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
      if (status.chars[i].name === charName)
        return Object.assign(status.chars[i], info);
    }
  }

  function updatePager(pager) {
    // pager = dict(cur_page=cur_page, doc_count=doc_count, page_size=page_size)
    let page_count = Math.ceil(pager['doc_count'] / pager['page_size']);
    $('.pagers .page-count').text(page_count);
    $('.pagers .cur-page').text(pager['cur_page']);
    $('.pagers .doc-count').text(pager['doc_count']);
    $('.pagers .p-prev').toggleClass('hide', pager['cur_page'] < 2);
    $('.pagers .p-next').toggleClass('hide', pager['cur_page'] >= page_count);

    let display_count = 5;
    let gap = Math.floor(display_count / 2), is_left = display_count % 2;
    let start = pager['cur_page'] - gap, end = pager['cur_page'] + gap - 1 + is_left;
    let offset = start < 1 ? 1 - start : page_count < end ? page_count - end : 0;
    start += offset;
    start = start < 1 ? 1 : start;
    end += offset;
    end = end > page_count ? page_count : end;

    let html = '';
    for (let i = start; i <= end; i++) {
      let cls = i === pager['cur_page'] ? 'p-no active' : 'p-no';
      html += `<li class="${cls}"><a>${i}</a></li>`;
    }
    $('.pagers li.p-no').remove();
    $('.pagers li.p-prev').after(html);
  }

}());