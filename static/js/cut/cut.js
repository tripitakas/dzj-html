/*
 * cut.js
 *
 * Date: 2019-05-08
 */
(function() {
  'use strict';

  function getDistance(a, b) {
    var cx = a.x - b.x, cy = a.y - b.y;
    return Math.sqrt(cx * cx + cy * cy);
  }

  // 得到字框矩形的控制点坐标
  function getHandle(el, index) {
    var box = el.getBBox();
    var pt;

    if (!box) {
      return {};
    }
    switch (index) {
      case 0:   // left top
        pt = [box.x, box.y];
        break;
      case 1:   // right top
        pt = [box.x + box.width, box.y];
        break;
      case 2:   // right bottom
        pt = [box.x + box.width, box.y + box.height];
        break;
      case 3:   // left bottom
        pt = [box.x, box.y + box.height];
        break;
      case 4:   // top center
        pt = [box.x + box.width / 2, box.y];
        break;
      case 5:   // right center
        pt = [box.x + box.width, box.y + box.height / 2];
        break;
      case 6:   // bottom center
        pt = [box.x + box.width / 2, box.y + box.height];
        break;
      case 7:   // left center
        pt = [box.x, box.y + box.height / 2];
        break;
      default:  // center
        pt = [box.x + box.width / 2, box.y + box.height / 2];
        break;
    }

    return {x: pt[0], y: pt[1]};
  }

  // 移动字框矩形的控制点，生成新的矩形
  function setHandle(el, index, pt) {
    var pts = [0, 0, 0, 0];

    for (var i = 0; i < 4; i++) {
      pts[i] = getHandle(el, Math.floor(index / 4) * 4 + i);
    }
    pts[index % 4] = pt;

    if (index >= 0 && index < 4) {
      if (index % 2 === 0) {
        pts[(index + 1) % 4].y = pt.y;
        pts[(index + 3) % 4].x = pt.x;
      } else {
        pts[(index + 1) % 4].x = pt.x;
        pts[(index + 3) % 4].y = pt.y;
      }
      var x1 = Math.min(pts[0].x, pts[1].x, pts[2].x, pts[3].x);
      var y1 = Math.min(pts[0].y, pts[1].y, pts[2].y, pts[3].y);
      var x2 = Math.max(pts[0].x, pts[1].x, pts[2].x, pts[3].x);
      var y2 = Math.max(pts[0].y, pts[1].y, pts[2].y, pts[3].y);
      return createRect({x: x1, y: y1}, {x: x2, y: y2});
    }
    else if (index >= 4 && index < 8) {
      return createRect({x: pts[3].x, y: pts[2].y}, {x: pts[1].x, y: pts[0].y});
    }
  }

  // 根据两个对角点创建字框图形，要求字框的面积大于等于100且宽高都至少为5，以避免误点出碎块
  function createRect(pt1, pt2, force) {
    var width = Math.abs(pt1.x - pt2.x), height = Math.abs(pt1.y - pt2.y);
    if (width >= 5 && height >= 5 && width * height >= 100 || force) {
      var x = Math.min(pt1.x, pt2.x), y = Math.min(pt1.y, pt2.y);
      return data.paper.rect(x, y, width, height)
        .initZoom().setAttr({
          stroke: data.changedColor,
          'stroke-opacity': data.boxOpacity,
          'stroke-width': 1.5 / data.ratioInitial   // 除以初始比例是为了在刚加载宽撑满显示时线宽看起来是1.5
          , fill: (data.blockMode || data.columnMode) && data.hoverFill
          , 'fill-opacity': 0.1
        });
    }
  }

  function findCharById(id) {
    return data.chars.filter(function(box) {
      return box.char_id === id;
    })[0];
  }

  function notifyChanged(el, reason) {
    var char = el && findCharById(el.data('cid'));
    data.boxObservers.forEach(function(func) {
      func(char || {}, el && el.getBBox(), reason);
    });
  }

  var HTML_DECODE = {
    '&lt;': '<',
    '&gt;': '>',
    '&amp;': '&',
    '&nbsp;': ' ',
    '&quot;': '"'
  };
  function decodeHtml(s) {
    s = s.replace(/&\w+;|&#(\d+);/g, function ($0, $1) {
      var c = HTML_DECODE[$0];
      if (c === undefined) {
        // Maybe is Entity Number
        if (!isNaN($1)) {
          c = String.fromCharCode(($1 === 160) ? 32 : $1);
        } else {
          // Not Entity Number
          c = $0;
        }
      }
      return c;
    });
    s = s.replace(/'/g, '"').replace(/: True/g, ': 1').replace(/: (False|None)/g, ': 0').replace(/\\/g, '/');
    return s;
  }

  var data = {
    normalColor: '#158815',                   // 正常字框的线色
    changedColor: '#C53433',                  // 改动字框的线色
    hoverColor: '#e42d81',                    // 掠过时的字框线色
    hoverFill: '#ff0000',                     // 掠过时的字框填充色
    handleColor: '#e3e459',                   // 字框控制点的线色
    handleFill: '#ffffff',                    // 字框控制点的填充色
    activeHandleColor: '#72141d',             // 活动控制点的线色
    activeHandleFill: '#0000ff',              // 活动控制点的填充色
    handleSize: 2.2,                          // 字框控制点的半宽
    boxFill: 'rgba(0, 0, 0, .01)',            // 默认的字框填充色，不能全透明
    boxOpacity: 0.7,                          // 字框线半透明度
    activeFillOpacity: 0.4,                   // 略过或当期字框的填充半透明度
    ratio: 1,                                 // 缩放比例
    unit: 5,                                  // 微调量
    paper: null,                              // Raphael 画布
    image: null,                              // 背景图
    chars: [],                                // OCR识别出的字框
    boxObservers: []                          // 字框改变的回调函数
  };

  var state = {
    hover: null,                              // 掠过的字框
    hoverStroke: 0,                           // 掠过的字框原来的线色
    hoverHandle: {handles: [], index: -1, fill: 0}, // 掠过的字框的控制点，fill为原来的填充色，鼠标离开框后变为0

    down: null,                               // 按下时控制点的坐标，未按下时为空
    downOrigin: null,                         // 按下的坐标
    edit: null,                               // 当前编辑的字框
    originBox: null,                          // 改动前的字框
    editStroke: 0,                            // 当前编辑字框原来的线色
    editHandle: {handles: [], index: -1, fill: 0}, // 当前编辑字框的控制点

    scrolling: []                             // 防止多余滚动
  };

  var undoData = {
    d: {},
    apply: null,

    load: function (name, apply) {
      console.assert(name && name.length > 1);
      this.apply = apply;
      this.d = JSON.parse(localStorage.getItem('cutUndo') || '{}');
      if (this.d.name !== name) {
        this.d = {name: name, level: 1};
        localStorage.removeItem('cutUndo');
      }
      if (this.d.level === 1) {
        this.d.stack = [$.cut.exportBoxes()];
      } else {
        this.apply(this.d.stack[this.d.level - 1]);
      }
    },
    _save: function () {
      localStorage.setItem('cutUndo', JSON.stringify(this.d));
    },
    change: function () {
      this.d.stack.length = this.d.level;
      this.d.stack.push($.cut.exportBoxes());
      if (this.d.stack.length > 20) {
        this.d.stack = this.d.stack.slice(this.d.stack.length - 20);
      }
      this.d.level = this.d.stack.length;
      this._save();
    },
    undo: function () {
      if (this.d.level > 1) {
        var cid = $.cut.getCurrentCharID();
        this.d.level--;
        this.apply(this.d.stack[this.d.level - 1]);
        this._save();
        $.cut.switchCurrentBox(cid && $.cut.findCharById(cid).shape);
      }
    },
    redo: function () {
      if (this.d.level < this.d.stack.length) {
        var cid = $.cut.getCurrentCharID();
        this.d.level++;
        this.apply(this.d.stack[this.d.level - 1]);
        this._save();
        $.cut.switchCurrentBox(cid && $.cut.findCharById(cid).shape);
      }
    },
    canUndo: function () {
      return this.d.level > 1;
    },
    canRedo: function () {
      return this.d.level < this.d.stack.length;
    }
  };

  $.cut = {
    data: data,
    state: state,
    getDistance: getDistance,

    decodeJSON: function (text) {
      return JSON.parse(decodeHtml(text));
    },

    showHandles: function(el, handle) {
      var i, pt, r;
      var size = data.handleSize;

      for (i = 0; i < handle.handles.length; i++) {
        handle.handles[i].remove();
      }
      handle.handles.length = 0;

      if (el && !state.readonly) {
        for (i = 0; i < 8; i++) {
          pt = getHandle(el, i);
          r = data.paper.rect(pt.x - size, pt.y - size, size * 2, size * 2)
            .attr({
              stroke: i === handle.index ? data.activeHandleColor : data.hoverColor,
              fill: i === handle.index ? data.activeHandleFill : data.handleFill,
              'fill-opacity': i === handle.index ? 0.8 : data.activeFillOpacity,
              'stroke-width': 1.2   // 控制点显示不需要放缩自适应，所以不需要调用 initZoom()
            });
          handle.handles.push(r);
        }
      }
    },

    activateHandle: function(el, handle, pt) {
      var dist = handle.fill ? 200 : 8;
      var d, i;

      handle.index = -1;
      for (i = el && pt ? 7 : -1; i >= 0; i--) {
        d = getDistance(pt, getHandle(el, i));
        if (dist > d) {
          dist = d;
          handle.index = i;
        }
      }
      this.showHandles(el, handle);
    },

    hoverIn: function(box) {
      if (box && box !== state.edit) {
        state.hover = box;
        state.hoverHandle.index = -1;
        state.hoverStroke = box.attr('stroke');
        state.hoverHandle.fill = box.attr('fill');
        state.hoverHandle.hidden = box.node.style.display === 'none';
        box.attr({
          stroke: data.hoverColor,
          'stroke-opacity': data.boxOpacity
        });
      }
    },

    hoverOut: function(box) {
      if (box && state.hover === box && state.hoverHandle.fill) {
        box.attr({ stroke: state.hoverStroke, fill: state.hoverHandle.fill });
        state.hoverHandle.fill = 0;   // 设置此标志，暂不清除 box 变量，以便在框外也可点控制点
        if (state.hoverHandle.hidden) {
          box.hide();
        }
      }
      else if (box && state.edit === box && state.editHandle.fill) {
        box.attr({ stroke: state.editStroke, fill: state.editHandle.fill });
        if (state.editHandle.hidden) {
          box.hide();
        }
        state.editHandle.fill = 0;
      }
    },

    scrollToVisible: function(el, ms) {
      var self = this;
      var bound = data.holder.getBoundingClientRect();  // 画布相对于视口的坐标范围，减去滚动原点
      var box = el.getBBox();                           // 字框相对于画布的坐标范围
      var win = data.scrollContainer || $(window);      // 有滚动条的画布容器窗口
      var st = win.scrollTop(), sl = win.scrollLeft(), w = win.innerWidth(), h = win.innerHeight();
      var scroll = 0;

      if (!box) {
        return;
      }
      if (data.scrollContainer) {
        var parentRect = data.scrollContainer[0].getBoundingClientRect();
        bound.y -= parentRect.y;
        bound.x -= parentRect.x;
      }

      var boxBottom = box.y + box.height + bound.y + 10 + st;
      var boxTop = box.y + bound.y - 10 + st;
      var boxRight = box.x + box.width + bound.x + 10 + sl;
      var boxLeft = box.x + bound.x - 10 + sl;

      // 字框的下边缘在可视区域下面，就向上滚动
      if (boxBottom - st > h) {
        st = boxBottom - h;
        scroll++;
      }
      // 字框的上边缘在可视区域上面，就向下滚动
      else if (boxTop < st) {
        st = boxTop;
        scroll++;
      }
      // 字框的右边缘在可视区域右侧，就向左滚动
      if (boxRight - sl > w) {
        sl = boxRight - w;
        scroll++;
      }
      // 字框的左边缘在可视区域左面，就向右滚动
      else if (boxLeft < sl) {
        sl = boxLeft;
        scroll++;
      }
      if (scroll) {
        state.scrolling.push(el);
        if (state.scrolling.length === 1 || ms) {
          (data.scrollContainer || $('html,body')).animate(
            {scrollTop: st, scrollLeft: sl}, ms || 500,
            function() {
              var n = state.scrolling.length;
              el = n > 1 && state.scrolling[n - 1];
              state.scrolling.length = 0;
              if (el) {
                self.scrollToVisible(el, 300);
              }
            });
        }
      }
    },
    
    switchCurrentBox: function(el) {
      this.hoverOut(state.hover);
      this.hoverOut(state.edit);
      state.hover = null;
      this.showHandles(state.hover, state.hoverHandle);

      el = typeof el === 'string' ? (this.findCharById(el) || {}).shape : el;
      state.edit = el;
      if (el) {
        state.editStroke = el.attr('stroke');
        state.editHandle.fill = el.attr('fill');
        state.editHandle.hidden = el.node && el.node.style.display === 'none';
        el.attr({
          stroke: data.changedColor,
          fill: data.hoverFill,
          'stroke-opacity': data.boxOpacity,
          'fill-opacity': data.activeFillOpacity
        });
        el.show();
        this.scrollToVisible(el);
      }
      this.showHandles(state.edit, state.editHandle);
      notifyChanged(state.edit, 'navigate');
    },

    // 创建校对画布和各个框
    create: function(p) {
      var self = this;

      var getPoint = function(e) {
        var svg = data.holder.getElementsByTagName('svg');
        var box = svg[0].getBoundingClientRect();
        return { x: e.clientX - box.x, y: e.clientY - box.y };
      };

      var mouseHover = function(e) {
        var pt = getPoint(e);
        var box = e.shiftKey ? null : self.findBoxByPoint(pt, e.altKey);

        if (state.hover !== box) {
          self.hoverOut(state.hover);
          self.hoverIn(box);
        }
        if (box === state.edit) {
          self.activateHandle(state.edit, state.editHandle, pt);
          state.hover = null;
          self.showHandles(null, state.hoverHandle);
        } else {
          state.editHandle.index = -1;
          self.showHandles(null, state.editHandle);
          self.activateHandle(state.hover, state.hoverHandle, pt);
        }

        if (state.hover && !state.hoverHandle.fill && state.hoverHandle.index < 0) {
          self.hoverOut(state.hover);
          state.hover = null;
          self.showHandles(state.hover, state.hoverHandle);
        }
        e.preventDefault();
      };

      var mouseDown = function(e) {
        e.preventDefault();
        if (e.button === 2) { // right button
          return;
        }
        state.downOrigin = state.down = getPoint(e);
        state.focus = true;
        if ($.fn.mapKey) {
          $.fn.mapKey.enabled = true;
        }

        // 鼠标略过控制点时，当前字框的控制点不能被选中，则切换为另外已亮显热点控制点的字框
        var lockBox = e.altKey;
        if (e.shiftKey) {
          self.switchCurrentBox(null);
        }
        else if ((!state.edit || state.editHandle.index < 0) && !lockBox) {
          self.switchCurrentBox(state.hover);
        }
        // 检测可以拖动当前字框的哪个控制点，能拖动则记下控制点的拖动起始位置
        self.activateHandle(state.edit, state.editHandle, state.down);
        if (state.editHandle.index >= 0) {
          state.down = getHandle(state.edit, state.editHandle.index);
        }
        else if (!lockBox) {
          // 不能拖动当前字框的控制点，则取消当前字框的高亮显示，准备画出一个新字框
          self.hoverOut(state.edit);
          state.edit = null;
          notifyChanged(state.edit, 'navigate');
        }

        // 不能拖动当前字框的控制点，则画出一个新字框
        if (!state.edit && !state.readonly) {
          state.editHandle.index = 2;  // 右下角为拖动位置
          state.edit = createRect(state.down, state.down, true);
        }
      };

      var mouseDrag = function(e) {
        var pt = getPoint(e);

        e.preventDefault();
        if (state.readonly || !state.originBox && getDistance(pt, state.downOrigin) < 3) {
          return;
        }

        var box = setHandle(state.originBox || state.edit, state.editHandle.index, pt);
        if (box) {
          // 刚开始改动，记下原来的图框并变暗，改完将删除，或放弃改动时(cancelDrag)恢复属性
          if (!state.originBox) {
            state.originBox = state.edit;
            state.originBox.attr({stroke: 'rgba(0, 255, 0, 0.8)', 'opacity': 0.1});
          } else {
            state.edit.remove();    // 更新字框形状
          }
          state.edit = box;
        }
        self.showHandles(state.edit, state.editHandle);
      };

      var mouseUp = function(e) {
        e.preventDefault();
        if (state.down) {
          var pt = getPoint(e);
          if (state.originBox && getDistance(pt, state.down) > 1) {
            self._changeBox(state.originBox, state.edit);
          }
          else {
            self.cancelDrag();
            self.switchCurrentBox(state.edit);
          }
        }
      };

      self.destroy();
      data.paper = Raphael(p.holder, p.width, p.height).initZoom();
      data.holder = document.getElementById(p.holder);
      state.focus = true;

      data.image = data.paper.image(p.image, 0, 0, p.width, p.height);
      data.board = data.paper.rect(0, 0, p.width, p.height)
        .attr({'stroke': 'transparent', fill: data.boxFill});

      state.readonly = p.readonly;
      data.blockMode = p.blockMode;
      data.columnMode = p.columnMode;
      if (p.blockMode || p.columnMode) {
        data.activeFillOpacity = 0.3;
      }
      data.ratioInitial = ($(data.holder).width() - 20) / p.width;
      data.scrollContainer = p.scrollContainer && $(p.scrollContainer);
      $(data.holder)
        .mousedown(mouseDown)
        .mouseup(mouseUp)
        .mousemove(function(e) {
          (state.down ? mouseDrag : mouseHover)(e);
        });

      var xMin = 1e5, yMin= 1e5, leftTop = null;

      if (typeof p.chars === 'string') {
        p.chars = self.decodeJSON(p.chars);
      }

      p.chars.forEach(function(b, idx) {
        if (p.columnMode) {
          b.char_id = b.column_id;
        }
        if (b.char_id) {
          var ids = b.char_id.replace('b', 'c').split('c');
          if (ids.length > 2) {
            b.block_no = parseInt(ids[1]);
            b.line_no = parseInt(ids[2]);
            b.char_no = parseInt(ids[3]);
          }
        }
        if (b.block_no && b.line_no && b.char_no && !b.char_id) {
          b.char_id = (b.block_no * 1000 + b.line_no) + 'n' + (b.char_no > 9 ? b.char_no : '0' + b.char_no);
        }
        if (!b.char_id) {
          b.char_id = 'org' + idx;
        }
      });
      data.width = p.width;
      data.height = p.height;
      data.chars = p.chars;
      data.removeSmall = p.removeSmallBoxes && [40, 40];
      self._apply(p.chars, 1);

      p.chars.forEach(function(b) {
        if (yMin > b.y - data.unit && xMin > b.x - data.unit) {
          yMin = b.y;
          xMin = b.x;
          leftTop = b.shape;
        }
      });
      self.switchCurrentBox(leftTop);
      self.setRatio(1);
      undoData.load(p.name, self._apply.bind(self));

      return data;
    },

    // 销毁所有图形
    destroy: function() {
      if (data.image) {
        data.image.remove();
        delete data.image;
      }
      if (data.board) {
        data.board.remove();
        delete data.board;
      }
      data.chars.forEach(function(b) {
        if (b.shape) {
          b.shape.remove();
          delete b.shape;
        }
      });
      if (data.paper) {
        data.paper.remove();
        delete data.paper;
      }
    },

    switchPage: function (name, pageData) {
      this.setRatio();
      state.hover = state.edit = null;
      $.extend(data, pageData);
      undoData.load(name, this._apply.bind(this));
      this.navigate('left');
    },

    _apply: function (chars, ratio) {
      var self = this;
      var s = ratio || data.ratio * data.ratioInitial;
      var cid = this.getCurrentCharID();

      data.chars.forEach(function(b) {
        if (b.shape) {
          b.shape.remove();
          delete b.shape;
        }
      });
      chars.forEach(function(b) {
        if (data.removeSmall && b.ch !== '一' && (
            b.w < data.removeSmall[0] / 2 && b.h < data.removeSmall[1] / 2
            || b.w < data.removeSmall[0] / 3 || b.h < data.removeSmall[1] / 3)) {
          return;
        }
        var c = self.findCharById(b.char_id);
        if (!c) {
          c = JSON.parse(JSON.stringify(b));
          data.chars.push(c);
        }
        c.shape = data.paper.rect(b.x * s, b.y * s, b.w * s, b.h * s).initZoom()
          .setAttr({
            stroke: data.normalColor,
            'stroke-opacity': data.boxOpacity,
            'stroke-width': 1.5 / data.ratioInitial   // 除以初始比例是为了在刚加载宽撑满显示时线宽看起来是1.5
            , fill: (data.blockMode || data.columnMode) && data.hoverFill
            , 'fill-opacity': 0.1
          })
          .data('cid', b.char_id)
          .data('char', b.ch);

        if (b.char_id && parseInt(b.char_id.split('c')[2]) > 100) {
          setTimeout(function () {
            c.shape.attr({fill: data.hoverFill, 'fill-opacity': 0.8});
            c.shape.show();
          }, 100);
        }
      });
      var char = this.findCharById(cid);
      this.switchCurrentBox(char && char.shape);
    },

    undo: undoData.undo.bind(undoData),
    redo: undoData.redo.bind(undoData),
    canUndo: undoData.canUndo.bind(undoData),
    canRedo: undoData.canRedo.bind(undoData),

    _changeBox: function(src, dst) {
      if (!dst) {
        return;
      }

      var info = src && this.findCharById(src.data('cid')) || {};
      var added = !info.char_id;

      if (added) {
        for (var i = 1; i < 999; i++) {
          info.char_id = 'new' + i;
          if (!this.findCharById(info.char_id)) {
            data.chars.push(info);
            break;
          }
        }
      } else {
        info.changed = true;
      }
      dst.data('cid', info.char_id).data('char', dst.ch);
      info.shape = dst;
      if (added) {
        notifyChanged(dst, 'added');
      }

      if (src) {
        dst.insertBefore(src);
        src.remove();
      }
      state.originBox = null;
      state.edit = state.down = null;
      undoData.change();
      notifyChanged(dst, 'changed');
      this.switchCurrentBox(dst);

      return info.char_id;
    },

    getCurrentCharID: function() {
      return state.edit && state.edit.data('cid');
    },

    getCurrentChar: function() {
      return state.edit && state.edit.data('char');
    },

    findCharById: findCharById,

    findCharsByLine: function(block_no, line_no, cmp) {
      return data.chars.filter(function(box) {
        return box.block_no === block_no && box.line_no === line_no && (!cmp || cmp(box.ch, box));
      }).sort(function(a, b) {
        return a.char_no - b.char_no;
      });
    },

    findBoxByPoint: function(pt, lockBox) {
      var ret = null, dist = 1e5, d, i, j, el;
      var isInRect = function(el, tol) {
        var box = el && el.getBBox();
        return box && pt.x > box.x - tol &&
          pt.y > box.y - tol &&
          pt.x < box.x + box.width + tol &&
          pt.y < box.y + box.height + tol;
      };

      if (state.edit && (isInRect(state.edit, state.readonly ? 1 : 10) || lockBox)) {
        return state.edit;
      }
      for (i = 0; i < data.chars.length; i++) {
        el = data.chars[i].shape;
        if (el && isInRect(el, 5)) {
          for (j = 0; j < 8; j++) {
            d = getDistance(pt, getHandle(el, j)) + (el === state.edit ? 0 : 5);
            if (dist > d) {
              dist = d;
              ret = el;
            }
          }
        }
      }
      return ret;
    },

    exportBoxes: function(pageData) {
      var r = function(v) {
        return Math.round(v * 10 / pageData.ratio / pageData.ratioInitial) / 10;
      };
      pageData = pageData || data;
      return pageData.chars.filter(function(c) { return c.shape && c.shape.getBBox(); }).map(function(c) {
        var box = c.shape.getBBox();
        c = $.extend({}, c, {x: r(box.x), y: r(box.y), w: r(box.width), h: r(box.height)});
        delete c.shape;
        Object.keys(c).forEach(function (k) {
          if (c[k] === null) {
            delete c[k];
          }
        });
        return c;
      });
    },

    // callback: function(info, box, reason)
    onBoxChanged: function(callback) {
      data.boxObservers.push(callback);
    },

    cancelDrag: function() {
      if (state.originBox) {
        state.edit.remove();
        state.edit = state.originBox;
        state.edit.attr('opacity', 1);
        delete state.originBox;
      }
      if (state.edit && state.edit.getBBox().width < 1) {
        state.edit.remove();
        state.edit = null;
      }
      else if (state.edit && state.editHandle.fill) {
        state.edit.attr({
          stroke: state.editStroke,
          fill: state.editHandle.fill
        });
        if (state.editHandle.hidden) {
          state.edit.hide();
        }
        state.editHandle.fill = 0;
      }
      state.down = null;
    },

    removeBox: function() {
      this.cancelDrag();
      if (state.edit && !state.readonly) {
        var el = state.edit;
        var info = this.findCharById(el.data('cid'));
        var hi = /small|narrow|flat/.test(data.hlType) && this.switchNextHighlightBox;
        var next = hi ? this.switchNextHighlightBox(1) : this.navigate('down');

        if (next === info.char_id) {
          next = hi ? this.switchNextHighlightBox(-1) : this.navigate('left');
          if (next === info.char_id) {
            this.navigate('right');
          }
        }
        info.shape = null;
        el.remove();
        undoData.change();
        notifyChanged(el, 'removed');

        return info.char_id;
      }
    },

    addBox: function() {
      this.cancelDrag();
      var box = state.edit && state.edit.getBBox();
      if (box) {
        var dx = box.width / 2, dy = box.height / 2;
        var newBox = createRect({x: box.x + dx, y: box.y + dy},
          {x: box.x + box.width + dx, y: box.y + box.height + dy});
        return this._changeBox(null, newBox);
      }
    },

    findCharByData: function(key, value) {
      return value && data.chars.filter(function (box) {
        return box.shape && box.shape.data(key) === value;
      })[0];
    },

    navigate: function(direction) {
      var i, cur, chars, calc, invalid = 1e5;
      var minDist = invalid, d, ret;

      chars = data.chars.filter(function(c) { return c.shape; });
      ret = cur = state.edit || state.hover || (chars[chars.length - 1] || {}).shape;
      cur = cur && cur.getBBox();

      if (!cur) {
        return;
      }
      if (direction === 'left' || direction === 'right') {
        calc = function(box) {
          // 排除水平反方向的框：如果方向为left，则用当前框右边的x来过滤；如果方向为right，则用当前框左边的x来过滤
          var dx = direction === 'left' ? (box.x + box.width - cur.x - cur.width) : (box.x - cur.x);
          if (direction === 'left' ? dx > -2 : dx < 2) {
            return invalid;
          }
          // 找中心点离得近的，优先找X近的，不要跳到较远的其他栏
          var dy = Math.abs(box.y + box.height / 2 - cur.y - cur.height / 2);
          if (dy > Math.max(cur.height, box.height) * 5) {  // 可能是其他栏
            return invalid;
          }
          return dy * 2 + Math.abs(dx);
        };
      }
      else {
        calc = function(box) {
          // 排除垂直反方向的框：如果方向为up，则用当前框下边的y来过滤；如果方向为down，则用当前框上边的y来过滤；不在同一列的则加大过滤差距
          var dy = direction === 'up' ? (box.y + box.height - cur.y - cur.height) : (box.y - cur.y);
          var gap = box.x < cur.x ? cur.x - box.x - box.width : box.x - cur.x - cur.width;
          var overCol = gap > box.width / 8;
          if (direction === 'up' ? dy > (overCol ? -box.height / 2 : -2) : dy < (overCol ? box.height / 2 : 2)) {
            return invalid;
          }
          // 找中心点离得近的，优先找Y近的，不要跳到较远的其他列
          var dx = Math.abs(box.x + box.width / 2 - cur.x - cur.width / 2);
          if (dx > Math.max(cur.width, box.width) * 5) {
            return invalid;
          }
          return dx * 2 + Math.abs(dy);
        };
      }

      // 找加权距离最近的字框
      for (i = 0; i < chars.length; i++) {
        d = chars[i].shape ? calc(chars[i].shape.getBBox()) : invalid;
        if (minDist > d) {
          minDist = d;
          ret = chars[i].shape;
        }
      }

      if (ret) {
        this.cancelDrag();
        this.switchCurrentBox(ret);
        return ret.data('cid');
      }
    },

    moveBox: function(direction) {
      this.cancelDrag();
      var box = state.edit && state.edit.getBBox();
      if (box) {
        if (direction === 'left') {
          box.x -= data.unit;
        }
        else if (direction === 'right') {
          box.x += data.unit;
        }
        else if (direction === 'up') {
          box.y -= data.unit;
        }
        else {
          box.y += data.unit;
        }

        var newBox = createRect({x: box.x, y: box.y}, {x: box.x + box.width, y: box.y + box.height});
        return this._changeBox(state.edit, newBox);
      }
    },

    resizeBox: function(direction, shrink) {
      this.cancelDrag();
      var box = state.edit && state.edit.getBBox();
      if (box) {
        if (direction === 'left') {
          box.x += shrink ? data.unit : -data.unit;
          box.width += shrink ? -data.unit : data.unit;
        }
        else if (direction === 'right') {
          box.width += shrink ? -data.unit : data.unit;
        }
        else if (direction === 'up') {
          box.y += shrink ? data.unit : -data.unit;
          box.height += shrink ? -data.unit : data.unit;
        }
        else {
          box.height += shrink ? -data.unit : data.unit;
        }

        var newBox = createRect({x: box.x, y: box.y}, {x: box.x + box.width, y: box.y + box.height});
        return this._changeBox(state.edit, newBox);
      }
    },

    toggleBox: function(visible) {
      data.chars.forEach(function(box) {
        if (box.shape) {
          $(box.shape.node).toggle(visible);
        }
      });
    },

    setRatio: function(ratio) {
      var el = state.edit || state.hover;
      var box = el && el.getBBox();
      var body = document.documentElement || document.body;
      var pos = [body.scrollLeft, body.scrollTop];

      this.cancelDrag();
      this.hoverOut(state.hover);
      this.hoverOut(state.edit);
      if (data.blockMode && ratio !== 1) {
        return;
      }

      data.ratio = ratio;
      ratio *= data.ratioInitial;
      data.paper.setZoom(ratio);
      data.paper.setSize(data.width * ratio, data.height * ratio);

      this.switchCurrentBox(el);

      var box2 = el && el.getBBox();
      if (box && box2) {
        window.scrollTo(box2.x + box2.width / 2 - box.x - box.width / 2 + pos[0],
          box2.y + box2.width / 2 - box.y - box.width / 2 + pos[1]);
      }
    }

  };
}());
