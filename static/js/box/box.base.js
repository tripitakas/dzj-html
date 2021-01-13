/**
 * box.base.js is used for cutting chars within image by drawing rectangle boxes.
 * It is base on raphael: https://dmitrybaranovskiy.github.io/raphael/reference.html
 * Notice:
 * 1. box.base.js依赖于box.css和css box-holder类
 *    如果有画布，则画布将画在box-holder上；如果没有画布，则用page-img显示图片
 * 2. Raphael会将页面svg元素的属性存在内部变量element中，它不是实时的。如果用js直接修改svg元素的属性，
 *    element中的属性并不会同步更新。在使用时要留意这一点
 * 3. Raphael内部变量保存在box.elem中。box.elem的class有多种属性，通过这些属性来控制元素的显示效果。
 *    框的所有操作历史（包括此次和此前的增删改）在初始化时设置在class属性中，包括b-added/b-deleted/b-changed
 * 4. element的attrs属性保留的是初始的坐标，而getBBox函数返回的是zoom之后的坐标
 * 5. 事件函数回调：boxObservers/onBoxChanged/notifyChanged
 *    - 内部事件通过notifyChanged传给boxObservers中的函数
 *    - 内部或外部函数都可以通过onBoxChanged来捕获各种事件进行处理
 * Date: 2020-12-25
 */
(function () {
  'use strict';

  // 数据定义
  let data = {
    paper: null,                                    // Raphael画布
    holder: null,                                   // 画布所在的页面元素
    txtHolder: null,                                // 文本所在的页面元素
    image: {elem: null, width: null, height: null}, // 背景图
    showMode: null,                                 // 初始化的显示模式
    initRatio: 1,                                   // 框坐标初始化的缩放比例
    ratio: 1,                                       // Raphael画布当前的缩放比例
    boxes: [],                                      // 带坐标的box数据
    boxObservers: [],                               // box改变的回调函数
  };

  // 当前状态
  let status = {
    userId: '',                                     // 用户id
    boxMode: 'cut',                                 // cut/order
    readonly: true,                                 // 是否只读
    curBox: null,                                   // 当前框
    curBoxType: 'char',                             // 当前显示框的类型
    curNoType: 'char',                              // 当前显示序号类型
    curTxtType: 'txt',                              // 当前显示文本类型
  };

  $.box = {
    data: data,
    status: status,
    initSvg: initSvg,
    setParam: setParam,
    cmpBox: cmpBox,
    setBoxes: setBoxes,
    getBoxes: getBoxes,
    navigate: navigate,
    isOverlap: isOverlap,
    isDeleted: isDeleted,
    showBoxes: showBoxes,
    getBoxId: getBoxId,
    getMaxCid: getMaxCid,
    createBox: createBox,
    createRect: createRect,
    switchCurBox: switchCurBox,
    findFirstBox: findFirstBox,
    setCurBoxType: setCurBoxType,
    switchBoxType: switchBoxType,
    highlightBoxes: highlightBoxes,
    findBoxByPoint: findBoxByPoint,
    scrollToVisible: scrollToVisible,
    isInRect: isInRect,
    getCharTxt: getCharTxt,
    getPoint: getPoint,
    getDistance: getDistance,
    getHandlePt: getHandlePt,
    showNo: showNo,
    toggleNo: toggleNo,
    initTxt: initTxt,
    toggleTxt: toggleTxt,
    hasTxtType: hasTxtType,
    zoomImg: zoomImg,
    toggleImage: toggleImage,
    getImageOpacity: getImageOpacity,
    setImageOpacity: setImageOpacity,
    setRawImageRatio: setRawImageRatio,
    round: round,
    hasClass: hasClass,
    addClass: addClass,
    removeClass: removeClass,
    toggleClass: toggleClass,
    onBoxChanged: onBoxChanged,
    notifyChanged: notifyChanged,
  };

  /*
  * 初始化画布
  * holder为必选项。imgUrl为可选项，表示画布的背景图的url。
  * width/height为可选项，表示画布初始宽和高。如果没有设置，则仅显示图片，不设置画布。
  * showMode为可选项，表示缩放模式，可以为空，或者'width-full'/'height-full'/'no-scroll'。
  */
  function initSvg(holder, imgUrl, width, height, showMode) {
    // holder
    let hd = holder.substr(1);
    data.holder = holder.startsWith('#') ? document.getElementById(hd) : document.getElementsByClassName(hd)[0];
    // svg画布模式 or 纯图片模式
    if (!width) return initRawImage(showMode, imgUrl);
    // init image param
    let r = initImageRatio(showMode, width, height);
    // set paper and image
    data.paper = Raphael(data.holder, width * r, height * r);
    Object.assign(data.image, {width: width, height: height});
    data.image.elem = imgUrl && imgUrl.indexOf('err=1') < 0 && data.paper.image(imgUrl, 0, 0, width * r, height * r);
    if ($.fn.mapKey) $.fn.mapKey.enabled = true;
  }

  function initImageRatio(showMode, width, height) {
    data.initRatio = 1;
    data.showMode = showMode;
    data.image.width = width;
    data.image.height = height;
    let w = $(data.holder).width(), h = $(data.holder).height();
    let rw = ((h * width / w) < height ? w - 15 : w) / width;
    let rh = ((w * height / h) < width ? h - 20 : h - 5) / height;
    if (showMode === 'width-full') {
      data.initRatio = rw;
    } else if (showMode === 'height-full') {
      data.initRatio = rh;
    } else if (showMode === 'no-scroll') {
      data.initRatio = Math.min(rw, rh);
    }
    return data.initRatio;
  }

  function initRawImage(showMode, imgUrl) {
    data.showMode = showMode;
    $(data.holder).html('<div class="box-holder"><div class="page-img"><img src="' + imgUrl + '" alt="图片不存在"/></div></div>')
  }

  // 纯图片模式时，在windows.onload中设置缩放比例
  function setRawImageRatio() {
    if (!data.image.width) {
      let img = $(data.holder).find('.page-img img');
      initImageRatio(data.showMode, img.width(), img.height());
      zoomImg(1);
    }
  }

  function setParam(param) {
    if (param.userId !== undefined) status.userId = param.userId;
    if (param.boxMode !== undefined) status.boxMode = param.boxMode;
    if (param.readonly !== undefined) status.readonly = param.readonly;
  }

  function cmpBox(a, b) {
    // 1. 栏框>列框>字框>图框
    let t = {block: 1, column: 2, char: 3, image: 4};
    if (a.boxType !== b.boxType) return t[a.boxType] - t[b.boxType];
    // 2. 依次比较栏号、列号、字号
    let bno1 = a.block_no || 0, bno2 = b.block_no || 0;
    if (bno1 !== bno2) return bno1 - bno2;
    let cno1 = a.column_no || 0, cno2 = b.column_no || 0;
    if (cno1 !== cno2) return cno1 - cno2;
    return (a.char_no || 0) - (b.char_no || 0);
  }

  function isDeleted(box) {
    return box.op === 'deleted' || (box.deleted && box.op !== 'recovered');
  }

  function isOverlap(e1, e2) {
    let ext = 2 * data.ratio;
    let b1 = (e1.elem || e1).getBBox(), b2 = (e2.elem || e2).getBBox();
    let out = b1.x > b2.x2 - ext || b2.x > b1.x2 - ext || b1.y > b2.y2 - ext || b2.y > b1.y2 - ext;
    return !out;
  }

  function setBoxes(param, reset) {
    // reset boxes
    if (reset) {
      data.boxes.forEach((b) => b.elem.remove());
      data.boxes = [];
      1
    }
    // set boxType
    if (param.boxes) {
      if (param.boxType) param.boxes.forEach((b) => b.boxType = param.boxType);
      data.boxes.push(...param.boxes);
    }
    if (param.blocks) {
      param.blocks.forEach((b) => b.boxType = 'block');
      data.boxes.push(...param.blocks);
    }
    if (param.columns) {
      param.columns.forEach((b) => b.boxType = 'column');
      data.boxes.push(...param.columns);
    }
    if (param.chars) {
      param.chars.forEach((b) => b.boxType = 'char');
      data.boxes.push(...param.chars);
    }
    if (param.images) {
      param.images.forEach((b) => b.boxType = 'image');
      data.boxes.push(...param.images);
    }
    // set params and draw boxes
    data.boxes.sort(cmpBox).forEach(function (box, i) {
      box.idx = i;
      box.cid = box.cid || (getMaxCid(box.boxType) + 1);
      box.elem = createBox(box).attr({'id': box.boxType + box.cid + '#' + i});
    });
  }

  function getBoxes() {
    let blocks = [], columns = [], chars = [], images = [];
    data.boxes.forEach((b) => {
      if (isDeleted(b)) return;
      if (b.boxType === 'char') chars.push(b);
      if (b.boxType === 'block') blocks.push(b);
      if (b.boxType === 'image') images.push(b);
      if (b.boxType === 'column') columns.push(b);
    });
    return {blocks: blocks, columns: columns, chars: chars, images: images};
  }

  /**
   * 显示字框
   * @param boxType 显示哪个boxType的字框。如果为all，则显示所有
   * @param cids 显示哪些cid对应的字框。可选, 如果为空，则显示所有
   * @param reset 是否隐藏其它字框，可选
   */
  function showBoxes(boxType, cids, reset) {
    data.boxes.forEach(function (b, i) {
      if ((boxType === 'all' || boxType === b.boxType) && (!cids || cids.indexOf(b.cid) > -1)) {
        if (b.elem) {
          removeClass(b.elem, 'hide');
        } else {
          b.elem = createBox(b);
          b.elem.attr({'id': b.boxType + b.cid + '#' + i});
        }
      } else if (reset) {
        addClass(b, 'hide');
      }
    });
  }

  function setCurBoxType(boxType) {
    status.curBoxType = boxType;
  }

  function switchBoxType(boxType, show) {
    // 切换显示框类型，包括all/block/column/char/image
    let holder = $($.box.data.holder);
    holder.removeClass('hide-all show-all show-block show-column show-char show-image');
    if (show && boxType) {
      $.box.setCurBoxType(boxType);
      holder.addClass('show-' + boxType);
    } else {
      $.box.setCurBoxType('');
      holder.addClass('hide-all');
    }
  }

  function highlightBoxes(boxType, cids, reset) {
    data.boxes.forEach(function (b) {
      if ((boxType === 'all' || boxType === b.boxType) && (!cids || cids.indexOf(b.cid) > -1)) {
        if (!b.elem) showBoxes(b.boxType, [b.cid]);
        addClass(b.elem, 'highlight');
      } else if (reset) {
        removeClass(b.elem, 'highlight');
      }
    });
  }

  function scrollToVisible(elem, center) {
    if (elem && elem.elem) elem = elem.elem;
    if (!elem || !elem.getBBox()) return;
    let unit = 10;
    let patch = unit * data.ratio;
    let bb = elem.getBBox();
    let hd = $($.box.data.holder);
    let bd = $.box.data.holder.getBoundingClientRect();
    let vb = {x: hd.scrollLeft(), y: hd.scrollTop(), w: bd.width, h: bd.height};
    let cp = {scrollLeft: bb.x - bd.width / 2, scrollTop: bb.y - bd.height / 2};
    if (vb.x > bb.x) { // elem在视窗左侧
      hd.animate(center ? cp : {scrollLeft: bb.x - unit}, 500);
    }
    if (bb.x2 > vb.x + vb.w) { // elem在视窗右侧
      hd.animate(center ? cp : {scrollLeft: bb.x2 - vb.w + unit + patch}, 500);
    }
    if (vb.y > bb.y) { // elem在视窗上侧
      hd.animate(center ? cp : {scrollTop: bb.y - unit}, 500);
    }
    if (bb.y2 > vb.y + vb.h) { // elem在视窗下侧
      hd.animate(center ? cp : {scrollTop: bb.y2 - vb.h + unit + patch}, 500);
    }
  }

  function navigate(direction, boxType) {
    boxType = boxType || status.curBoxType;
    if (!boxType || status.isMulti) return;

    if (!status.curBox) {
      for (let i = 0, len = data.boxes.length; i < len; i++) {
        if (boxType === 'all' || data.boxes[i].boxType === boxType)
          return switchCurBox(data.boxes[i]);
      }
      return;
    }

    let cur = status.curBox.elem.getBBox();
    let d, calc, ret = null, minDist = 1e8, invalid = 1e8;
    if (direction === 'left' || direction === 'right') {
      calc = function (box) {
        if (direction === 'left' && (box.x > cur.x)) return invalid;
        if (direction === 'right' && (box.x2 < cur.x2)) return invalid;
        let dx = direction === 'left' ? (cur.x - box.x) : (box.x2 - cur.x2);
        let dy = Math.abs(box.y + box.height / 2 - cur.y - cur.height / 2);
        return dx * dx + 10 * dy * dy;
      };
    } else {
      calc = function (box) {
        if (direction === 'up' && (box.y > cur.y)) return invalid;
        if (direction === 'down' && (box.y2 < cur.y2)) return invalid;
        let dy = direction === 'up' ? (cur.y - box.y) : (box.y2 - cur.y2);
        let dx = Math.abs(box.x + box.width / 2 - cur.x - cur.width / 2);
        return 10 * dx * dx + dy * dy;
      };
    }

    data.boxes.forEach(function (box) {
      let pt = box.elem && box.elem.getBBox();
      if (!pt || isDeleted(box) || equal(box, status.curBox)) return;
      if (boxType !== 'all' && box.boxType !== boxType) return;
      d = calc(pt);
      if (d < minDist) {
        minDist = d;
        ret = box;
      }
    });
    if (!ret && (direction === 'down' || direction === 'up')) {
      let idx = data.boxes.indexOf(status.curBox);
      idx += direction === 'down' ? 1 : -1;
      if (idx < 0) idx = 0;
      if (idx > data.boxes.length - 1) idx = data.boxes.length - 1;
      ret = data.boxes[idx];
      if (boxType !== 'all' && ret.boxType !== boxType) ret = null;
    }
    switchCurBox(ret);
  }

  function findBoxByPoint(pt, boxType, func) {
    if (!pt || !pt.x) return;
    if (status.curBox && isInRect(pt, status.curBox.elem, 5))
      return status.curBox;

    let ret = null, dist = 1e5;
    data.boxes.forEach(function (box) {
      if (box.elem && (boxType === 'all' || box.boxType === boxType)
          && isInRect(pt, box.elem, 3)) {
        if (func && !func(box)) return;
        for (let j = 0; j < 8; j++) {
          let d = getDistance(pt, getHandlePt(box.elem, j));
          if (d < dist) {
            dist = d;
            ret = box;
          }
        }
      }
    });
    return ret;
  }

  function findFirstBox(boxType, cid) {
    for (let i = 0, len = data.boxes.length; i < len; i++) {
      let b = data.boxes[i];
      if ((boxType === 'all' || b.boxType === boxType) && !isDeleted(b) && (!cid || cid == b.cid))
        return b;
    }
  }

  function switchCurBox(box) {
    if (box) {
      if (!equal(box, status.curBox)) {
        removeClass(status.curBox, 'current');
        addClass(box, 'current');
        scrollToVisible(box, true);
        status.curBox = box;
      }
      switchCurTxt(box);
    } else {
      removeClass(status.curBox, 'current hover');
      status.curBox = null;
    }
    notifyChanged(box, 'switch');
  }

  /**
   * 根据两个对角点创建字框图形
   * transPos为真时，pt1、pt2是相对于当前画布的坐标，因此需要将坐标转换为相对于初始画布的坐标，然后再zoom至当前画布
   */
  function createRect(pt1, pt2, cls, transPos, force) {
    let r = transPos ? data.ratio : 1;
    let x = Math.min(pt1.x, pt2.x) / r, y = Math.min(pt1.y, pt2.y) / r;
    let w = Math.abs(pt1.x - pt2.x) / r, h = Math.abs(pt1.y - pt2.y) / r;
    if (w >= 2 && h >= 2 && w * h >= 9 || (force && w && h)) { // 检查字框面积、宽高最小值，以避免误点出碎块
      let a = w > 40 ? 40 : w < 6 ? 6 : w; // 宽度从6~40，对应线宽从0.75到1.5
      let rect = data.paper.rect(x, y, w, h).attr({'class': cls, 'stroke-width': 0.75 + 0.022 * (a - 6)});
      if (data.ratio !== 1) rect.initZoom(1).setZoom(data.ratio);
      return rect;
    }
  }

  function createBox(box, cls) {
    function getCls(box) {
      let names = ['box'];
      if (box.boxType) names.push(box.boxType);
      if (box.readonly) names.push('readonly');
      if (!isDeleted(box)) {
        let isOdd = box.char_no ? box.column_no % 2 : box.block_no % 2;
        names.push(isOdd ? 'odd' : 'even');
      }
      let boxHint = ['b-deleted', 'b-added', 'b-changed'].filter((op) => box[op.replace('b-', '')]).join(' ');
      if (boxHint) names.push(boxHint);
      return names.join(' ')
    }

    // 注：box的坐标始终是根据初始画布设置的，然后根据data.ratio转换至当前画布显示
    let r = data.initRatio;
    return createRect({x: box.x * r, y: box.y * r}, {x: box.x * r + box.w * r, y: box.y * r + box.h * r},
        cls || getCls(box), false, true);
  }

  function getMaxCid(boxType) {
    let maxCid = 0;
    data.boxes.forEach(function (box) {
      if (box.cid && box.cid > maxCid && (boxType === 'all' || boxType === box.boxType))
        maxCid = box.cid;
    });
    return maxCid;
  }

  function getBoxId(b) {
    let id = 'b' + (b['block_no'] || 0);
    if (b.boxType === 'block') return id;
    id += 'c' + (b['column_no'] || 0);
    if (b.boxType === 'column') return id;
    id += 'c' + (b['char_no'] || 0);
    if (b.boxType === 'char') return id;
  }

  function getCharTxt(b) {
    return b['txt'] || b['ocr_txt'] || '';
  }

  function getPoint(e) {
    let svg = data.holder.getElementsByTagName('svg')[0];
    let box = svg.getBoundingClientRect();
    return {x: e.clientX - box.x, y: e.clientY - box.y};
  }

  function isInRect(pt, el, tol) {
    if (el && el.elem) el = el.elem;
    let box = el && el.getBBox && el.getBBox();
    return box && pt.x > box.x - tol && pt.y > box.y - tol &&
        pt.x < box.x2 + tol && pt.y < box.y2 + tol;
  }

  function getDistance(a, b) {
    let cx = a.x - b.x, cy = a.y - b.y;
    return Math.sqrt(cx * cx + cy * cy);
  }

  // 得到字框矩形的控制点坐标
  function getHandlePt(el, index) {
    // el是raphael element
    let b = el && el.getBBox && el.getBBox();
    if (!b) return {};
    if (index === 0) return {x: b.x, y: b.y};                               // left top
    if (index === 1) return {x: b.x + b.width, y: b.y};                     // right top
    if (index === 2) return {x: b.x + b.width, y: b.y + b.height};          // right bottom
    if (index === 3) return {x: b.x, y: b.y + b.height};                    // left bottom
    if (index === 4) return {x: b.x + b.width / 2, y: b.y};                 // top center
    if (index === 5) return {x: b.x + b.width, y: b.y + b.height / 2};      // right center
    if (index === 6) return {x: b.x + b.width / 2, y: b.y + b.height};      // bottom center
    if (index === 7) return {x: b.x, y: b.y + b.height / 2};                // left center
    if (index === 8) return {x: b.x + b.width / 2, y: b.y + b.height / 2};  // center
  }

  //---序号相关---
  function showNo() {
    data.boxes.forEach(function (b, i) {
      if (isDeleted(b) || b.boxType === 'image')
        return addClass(b.noElem, 'hide');
      let no = b[b.boxType + '_no'] || '0';
      let noId = 'no-' + b.boxType + b.cid;
      if (b.noElem && (b.op || '') !== 'changed')
        return $('#' + noId + ' tspan').text(no);

      let w = b.elem.attrs.width, fs = 0;
      if (b.boxType !== 'char') { // 宽度从6~80，对应字号从6到32
        w = w > 80 ? 80 : w < 6 ? 6 : w;
        fs = 6 + round((w - 6) * 0.35, 1);
      } else { // 对角线从6~40，对应字号从6到20
        let a = Math.sqrt(w * b.elem.attrs.height);
        a = a > 40 ? 40 : a < 6 ? 6 : a;
        fs = Math.min(6 + round((a - 6) * 0.5, 1), 20);
      }

      b.noElem && b.noElem.remove();
      let center = getHandlePt(b.elem, 8);
      let parentNo = b.boxType === 'column' ? b.block_no : b.column_no;
      let cls = 'no no-' + b.boxType + (parentNo % 2 ? ' odd' : ' even');
      b.noElem = data.paper.text(center.x, center.y, no).attr({
        'class': cls, 'id': noId, 'font-size': fs * data.ratio
      });
    });
  }

  function toggleNo(boxType, show) {
    status.curNoType = boxType;
    $(data.holder).removeClass('show-block-no show-column-no show-char-no');
    if (boxType && show) {
      $(data.holder).addClass('show-' + boxType + '-no');
      showNo();
    }
  }

  //---文本相关---
  function initTxt(txtHolder, txtType, toolTip) {
    let html = '', blockNo = null, columnNo = null;
    data.boxes.forEach((b) => {
      if (b.boxType !== 'char' || isDeleted(b)) return;
      if (blockNo !== b.block_no) {
        html += (!blockNo ? '</div></div>' : '') + '<div class="block"><div class="line">';
        blockNo = b.block_no;
        columnNo = 1;
      } else if (columnNo !== b.column_no) {
        html += '</div><div class="line">';
        columnNo = b.column_no;
      }
      let attr = getTxtAttr(b);
      if (toolTip && attr.cls.replace('char', '').length > 1) {
        html += `<span id="idx-${b.idx}" class="${attr.cls}" data-toggle="tooltip" data-html="true" data-placement="bottom" title="${attr.tip}">${b[txtType] || '■'}</span>`;
      } else {
        html += `<span id="idx-${b.idx}" class="${attr.cls}">${b[txtType] || '■'}</span>`;
      }
    });
    html += '</div></div>';
    data.txtHolder = txtHolder;
    $(txtHolder).html(html);
  }

  function getTxtAttr(box) {
    let txts = [], cls = 'char', tips = [];
    if (box['txt']) {
      tips.push(`校对文本: ${box['txt']}`);
    }
    let ocr_char = (box['alternatives'] || '').split('')[0];
    if (ocr_char) {
      txts.push(ocr_char);
      tips.push(`字框OCR: ${ocr_char}`);
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
    if (box['txt'] !== '■' && txts.indexOf(box['txt']) < 0) cls += ' changed';
    return {cls: cls, tip: tips.join('<br>')};
  }

  function toggleTxt(txtType, show) {
    if (status.curTxtType === txtType) return;
    if (txtType && show) {
      status.curTxtType = txtType;
      $.map($(data.txtHolder).find('.char'), function (item) {
        let idx = $(item).attr('id').split('-')[1];
        let box = data.boxes[idx];
        $(item).text(box[txtType] || '■');
      })
    }
  }

  function switchCurTxt(box) {
    let holder = $(data.txtHolder);
    if (!data.txtHolder || !holder.length) return;
    holder.find('.current-txt').removeClass('current-txt');
    if (box && box.boxType === 'char') {
      let $this = holder.find('#idx-' + box.idx);
      $('.current-char').removeClass('current-char');
      $this.addClass('current-char');
      $('.current-line').removeClass('current-line');
      $this.parent().addClass('current-line');
      let hp = $(data.txtHolder).offset(), cp = $this.offset();
      if ((cp.top - hp.top > holder.height() + holder.scrollTop()) || (cp.top < hp.top)) {
        holder.animate({scrollTop: cp.top - hp.top - 10}, 500);
      }
    }
  }

  function hasTxtType(txtType) {
    let chars = getBoxes()['chars'];
    if (chars.length === 1 && txtType in chars[0]) return true;
    return chars.length >= 2 && txtType in chars[0] && txtType in chars[1];
  }

  $(document).on('click', '.char', function (e) {
    let idx = $(this).attr('id').split('-')[1];
    switchCurBox(data.boxes[idx]);
  });

  //---图片相关---
  /**
   * 缩放画布或图片
   * ratio：设置缩放比例，相对原始大小缩放；factor：设置缩放因子，从当前大小开始缩放
   */
  function zoomImg(ratio, factor) {
    data.ratio = ratio || data.ratio || 1; // 初始化比例
    if (factor) data.ratio *= factor;
    let image = data.image;
    if (image.elem) { // svg画布模式
      Raphael.maxStrokeWidthZoom = 0.5 + data.ratio * 0.5;
      data.paper.setZoom(data.ratio);
      let r = data.initRatio * data.ratio;
      data.paper.setSize(data.image.width * r, data.image.height * r);
      status.curBox && scrollToVisible(status.curBox, true);
      notifyChanged(null, 'zoom');
    } else { // 纯图片模式
      let img = $(data.holder).find('.page-img img');
      let r = data.initRatio * data.ratio;
      img.width(r * data.image.width).height(r * data.image.height);
    }
  }

  function toggleImage(show) {
    let image = data.image;
    if (image.elem) {
      show = show || image.elem.node.style.display === 'none';
      image.elem.node.style.display = show ? 'block' : 'none';
    } else {
      let img = $(data.holder).find('.page-img img');
      show = show || img.hasClass('hide');
      show ? img.removeClass('hide') : img.addClass('hide');
    }
  }

  function getImageOpacity() {
    let image = data.image;
    if (image.elem) {
      return data.image.elem.node.style.opacity;
    } else {
      return $(data.holder).find('.page-img img').attr('opacity');
    }
  }

  function setImageOpacity(opacity) {
    let image = data.image;
    if (image.elem) {
      data.image.elem.node.style.opacity = opacity;
    } else {
      let img = $(data.holder).find('.page-img img');
      img.css('opacity', opacity);
    }
  }

  //---功能函数---
  function equal(el1, el2) {
    if (el1 && el1.elem) el1 = el1.elem;
    if (el2 && el2.elem) el2 = el2.elem;
    return el1 && el2 && el1.id === el2.id;
  }

  function round(f, n) {
    let m = Math.pow(10, n || 1);
    return Math.round(f * m) / m;
  }

  function hasClass(elem, className) {
    if (elem && elem.elem) elem = elem.elem;
    if (!elem || !elem.attrs) return false;
    return elem.attr('class').split(' ').indexOf(className) > -1;
  }

  function addClass(elem, className) {
    if (elem && elem.elem) elem = elem.elem;
    if (!elem || !elem.attrs) return;
    let cNames = className.split(' ');
    let eNames = elem.attr('class').split(' ');
    cNames.forEach(function (cls) {
      if (cls.length && eNames.indexOf(cls) < 0) eNames.push(cls);
    });
    elem.attr({'class': eNames.filter((n) => n.length).join(' ')});
    return elem;
  }

  function removeClass(elem, className) {
    if (elem && elem.elem) elem = elem.elem;
    if (!elem || !elem.attrs) return;
    let cNames = className.split(' ');
    let eNames = elem.attr('class').split(' ');
    elem.attr({'class': eNames.filter((s) => s.length && cNames.indexOf(s) < 0).join(' ')});
    return elem;
  }

  function toggleClass(elem, className, op) {
    if (op !== undefined)
      op ? addClass(elem, className) : removeClass(elem, className);
    else
      hasClass(elem, className) ? removeClass(elem, className) : addClass(elem, className);
  }

  // 注册回调函数: function callback(box, reason, param)
  function onBoxChanged(callback) {
    data.boxObservers.push(callback);
  }

  // 调用回调函数
  function notifyChanged(box, reason, param) {
    data.boxObservers.forEach(function (func) {
      func && func(box, reason, param);
    });
  }

}());