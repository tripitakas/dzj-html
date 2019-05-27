/* global $ */
(function() {
  'use strict';

  var highlightBox;

  $.extend($.cut, {
    bindMatchingKeys: function() {
      var self = this;
      var data = self.data;
      var on = function(key, func) {
        $.mapKey(key, func, {direction: 'down'});
      };

      // 方向键：在字框间导航
      on('left', function() {
        self.navigate('left');
      });
      on('right', function() {
        self.navigate('right');
      });
      on('up', function() {
        self.navigate('up');
      });
      on('down', function() {
        self.navigate('down');
      });

      var oldChar = [0, '', 0];

      // 响应字框的变化，记下当前字框的关联信息
      self.onBoxChanged(function(info, box, reason) {
        oldChar[0] = box && info.shape && info.shape.data('order');
        oldChar[1] = box && info.shape && (info.shape.data('text') || info.shape.data('char')) || '';
        oldChar[2] = info;
        $('#order').val(oldChar[0] || '');

        if (reason === 'navigate') {
          var curId = info && info.shape && info.shape.data('cid') || '?';
          for (var cid in data.texts) {
            if (data.texts.hasOwnProperty(cid)) {
              var rect = data.texts[cid][0];
              rect.attr({
                stroke: cid !== curId ? 'rgba(0,0,0,.1)' : data.changedColor,
                'stroke-opacity': cid !== curId ? 0.1 : data.boxOpacity,
                fill: cid !== curId ? 'none' : data.hoverFill,
                'fill-opacity': cid !== curId ? 0 : 0.2
              });
            }
          }
        }
      });

      // 改变字框的行内字序号
      $('#order').change(function(event) {
        var order = parseInt($('#order').val());
        var info = oldChar[2];

        event.preventDefault();

        if (order && info && info.shape) {
          if (order !== oldChar[0]) {
            // 清除原来字框的关联信息
            var last = self.findCharByData('order', order);
            if (last) {
              self.removeBandNumber(last);
              last.char_no = oldChar[0] || 0;
              if (last.char_no) {
                last.char_id = 'b' + last.block_no + 'c' + last.line_no + 'c' + last.char_no;
              } else {
                last.line_no = 0;
                last.char_id = ''
              }
              if (last.shape) {
                last.shape.data('cid', last.char_id);
                last.order_changed = true;
              }
            }
            // 更新当前字框的关联信息
            self.removeBandNumber(info);
            oldChar[0] = order;
            info.char_no = order;
            info.block_no = $.cut.data.block_no;
            info.line_no = $.cut.data.line_no;
            info.char_id = 'b' + info.block_no + 'c' + info.line_no + 'c' + info.char_no;
            if (info.shape) {
              info.shape.data('cid', info.char_id);
              info.order_changed = true;
            }
            $.cut.data.chars.sort(function (a, b) {
              return a.char_id.localeCompare(b.char_id);
            });
            if (highlightBox) {
              highlightBox();
              $.cut.switchCurrentBox(info.shape);
            }
          }
        }
      });
    },
    
    showColumn: function (field, columns, id) {
      var self = this, data = this.data;
      if (self[field]) {
        self[field].remove();
        delete self[field];
      }
      var column = columns && id && columns.filter(function (c) {
        return id.indexOf('c') < 0 ? c.block_id === id : c.column_id === id;
      })[0];
      if (column) {
        var s = data.ratio * data.ratioInitial;
        self[field] = data.paper.rect(column.x * s, column.y * s, column.w * s, column.h * s)
          .attr({fill: id.indexOf('c') < 0 ? 'none' : 'rgba(0,128,0,.01)', stroke: 'rgba(0,0,255,.3)'});
      }
    },

    // 显示当前列字框的浮动文字面板
    showFloatingPanel: function(chars, content, refresh) {
      var box, offset;
      var self = this;
      var data = self.data;
      var s = data.ratio;
      highlightBox = refresh;

      // 计算字框的并集框、平移距离
      chars.forEach(function(c) {
        var p = c.shape && c.shape.getBBox();
        if (p) {
          if (!box) {
            box = $.extend({}, p);
          } else {
            box.x = Math.min(box.x, p.x);
            box.y = Math.min(box.y, p.y);
            box.x2 = Math.max(box.x2, p.x2);
            box.y2 = Math.max(box.y2, p.y2);
          }
        }
      });
      if (box) {
        box.width = box.x2 - box.x;
        if (box.x2 > self.data.width * self.data.ratioInitial * 0.75) {
          offset = -15 - box.width;
        } else {
          offset = box.width + 15;
        }
        box.x += offset;
      }

      // 显示浮动面板
      if (chars.length) {
        data.bandNumberBox = data.paper.rect(box.x - 5, box.y - 5, box.width + 10, box.y2 - box.y + 10)
          .attr({fill: '#fff', stroke: 'rgba(0,0,0,.2)'});
      }
      // 显示每个字框的浮动序号框
      chars.forEach(function(c, i) {
        var el = c.shape;
        var p = el && el.getBBox();
        var text = content(c, i);
        if (p) {
          el.data('order', c.char_no);
          el.data('text', text);
          data.texts = data.texts || {};
          data.texts[el.data('cid')] = data.texts[el.data('cid')] || [
              data.paper.rect(p.x + offset, p.y, p.width, p.height)
                .attr({stroke: 'rgba(0,0,0,.3)'}),
              data.paper.text(p.x + p.width / 2 + offset, p.y + p.height / 2, '' + text)
                .attr({'font-size': 11 * Math.min(s, 1.5), 'text-align': 'center', stroke: '#44f'}),
              data.paper.rect(p.x, p.y, p.width, p.height)
                .attr({stroke: 'rgba(0,0,0,.4)'})
            ]
        }
      });
    },

    removeBandNumber: function (char, all) {
      var data = this.data;
      if (!char) {
        if (all && data.bandNumberBox) {
          data.bandNumberBox.remove();
          delete data.bandNumberBox;
        }
        return all && data.chars.forEach(function (c) {
            if (c.shape) {
              $.cut.removeBandNumber(c);
            }
          });
      }
      var el = char.shape;
      var arr = el && (data.texts || {})[el.data('cid')];
      if (arr) {
        delete data.texts[char.shape && char.shape.data('cid')];
        arr.forEach(function (p) {
          p.remove();
        });
        var text = el.data('text');
        el.removeData('order');
        el.removeData('text');
        return text;
      }
    }
  });
}());
