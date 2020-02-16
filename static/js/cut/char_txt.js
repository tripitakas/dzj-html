/*
 * char_txt.js
 * 分列显示的单字校对页面
 * Date: 2020-01-29
 * global $
 */

Array.max = Array.max || function(array) {
  return Math.max.apply(Math, array);
};

Array.min = Array.min || function(array) {
  return Math.min.apply(Math, array);
};

(function () {
  'use strict';

  var data = $.cut.data;
  var state = $.cut.state;

  // 列框单元类，有列图和分离的字框
  function ColNode(column, chars, left, top) {
    this.column = column;
    this.chars = chars;
    this.left = left;
    this.right = left + 2 * column.w + 12;
    this.top = top;
    this.bottom = top + column.h;
  }

  ColNode.prototype = {
    getId: function() {
      return this.column.column_id;
    },

    // 得到偏移后的字框
    pickChars: function(arr) {
      var self = this, left = this.left + this.column.w + 4;
      this.chars.forEach(function(c) {
        c._box = {
          'class': 'char',
          x: c.x - self.column.x + left,
          y: c.y - self.column.y + self.top,
          w: c.w, h: c.h,
          block_no: c.block_no, column_no: c.column_no, char_no: c.char_no, no: c.no,
          char_id: c.char_id, cid: c.cid, txt: c.txt,
          _char: c, _col: self
        };
        arr.push(c._box);
      });
      arr.push({
          'class': 'column', _col: self, fillOpacity: 0.1,
          x: self.left, y: self.top,
          w: self.column.w, h: self.column.h,
          block_no: self.column.block_no, column_no: self.column.column_no,
          column_id: self.column.column_id
        });
    },

    // 在字框内显示单字文字
    createText: function() {
      var ratio = data.ratioInitial * data.ratio;
      this.chars.forEach(function(c) {
        if (c._text) {
          c._text.remove();
          c._text = null;
        }
        if (c._box && c.txt && '?N□'.indexOf(c.txt) < 0) {
          var x = c._box.x + c.w / 2, y = c._box.y + c.h / 2;
          c._text = data.paper.text(x * ratio, y * ratio, c.txt)
            .attr({'font-size': $.cut.data.fontSize});
        }
      });
    },

    // 创建列框图
    createImage: function(url, width, height) {
      var c = this.column;
      var s = data.ratioInitial * data.ratio;
      if (this.img) {
        this.img.remove();
      }
      this.img = data.paper.image(url, (this.left - c.x) * s, (this.top - c.y) * s, width * s, height * s)
        .attr({'clip-rect': (this.left * s) + ',' + (this.top * s) + ',' + (c.w * s) + ',' + (c.h * s)})
        .data('id', this.getId())
        .data('node', this)
        .toBack();
    },

    // 得到由每个字框组成的列文本
    getText: function() {
      return this.chars.sort(function(a, b) {
        return a.char_no - b.char_no;
      }).map(function(c) {
        return c.txt;
      }).join('');
    }
  };

  // 列框集合类
  function ColNodes(image, width, height) {
    this.nodes = [];
    this.image = image;
    this.width = width;
    this.height = height;
  }

  ColNodes.prototype = {
    // 根据列框编号查找列框单元
    findColumnById: function(id) {
      return this.nodes.filter(function(c) {
        return c.getId() === id;
      })[0];
    },

    initLayout: function (data) {
      var self = this, yb = 10, boxes = [];
      var widths = data.blocks.map(function(block) {
        var columns = data.columns.filter(function(column) {  // 该栏的所有列框，靠左的在前
          return column.block_no === block.block_no;
        }).sort(function(a, b) {
          return a.x - b.x;
        });
        var left = 10, top = yb, count = 0;
        var nodes = [];

        while (columns.length) {
          columns.splice(Math.max(0, columns.length - 6), 6).forEach(function(column) {
            var chars = data.orgChars.filter(function(char) {
              return char.block_no === block.block_no && char.column_no === column.column_no;
            });
            var node = new ColNode(column, chars, left, top);
            self.nodes.push(node);
            nodes.push(node);
            node.pickChars(boxes);
            yb = Math.max(yb, node.bottom);
            left = node.right;
          });
          count = 0;
          left = 10;
          top = yb + 20;
        }

        yb += 20;
        return Array.max(nodes.map(function(c) {
          return c.right;
        }));
      });

      return {width: Array.max(widths) + 10, height: yb, boxes: boxes};
    }
  };

  $.extend($.cut, {
    createColumns: function (p) {
      var self = this;

      data.orgChars = typeof p.chars === 'string' ? self.decodeJSON(p.chars) : p.chars;
      data.columns = typeof p.columns === 'string' ? self.decodeJSON(p.columns) : p.columns;
      data.blocks = typeof p.blocks === 'string' ? self.decodeJSON(p.blocks) : p.blocks;

      data.cs = new ColNodes(p.image, p.width, p.height);
      data.boxOpacity = 0.2;
      var size = data.cs.initLayout(data);
      self.create({
        readonly: true,
        scrollContainer: p.scrollContainer,
        holder: p.holder,
        name: p.name,
        width: size.width,
        height: size.height,
        chars: size.boxes,
        widthFull: true,
        minRatio: 0.4
      });
      createImageText();
    },

    applyTxt: function(txt) {
      var c = this.findCharById(this.getCurrentCharID());
      if (txt && c && c.txt !== txt) {
        c._char.ch = c._char.txt = c.txt = txt;
        c._col.createText();
        state.edit.data('char', txt);
        state.editHandle.fill = '#f00';
        state.editHandle.fill = '#00f';
        state.editHandle.fillOpacity = 0.15;
        return c;
      }
    },

    exportBoxes: function() {
      return data.orgChars.map(function(c) {
        var r = {};
        Object.keys(c).forEach(function(k) {
          if (k[0] != '_' && ['shape', 'ch'].indexOf(k) < 0) {
            r[k] = c[k];
          }
        });
        return r;
      });
    }
  });

  function createImageText() {
    data.cs.nodes.forEach(function(c) {
      c.createText();
      c.createImage(data.cs.image, data.cs.width, data.cs.height);
    });
  }

  $.cut.onBoxChanged(function(info, box, reason) {
    if (reason === 'zoomed') {
      createImageText();
    }
  });

}());
