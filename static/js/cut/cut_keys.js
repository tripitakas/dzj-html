/* global $ */
(function() {
  'use strict';

  $.extend($.cut, {
    bindKeys: function() {
      var self = this;
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

      // w a s d：移动当前字框
      on('a', function() {
        self.moveBox('left');
      });
      on('d', function() {
        self.moveBox('right');
      });
      on('w', function() {
        self.moveBox('up');
      });
      on('s', function() {
        self.moveBox('down');
      });

      // alt+方向键：缩小字框
      on('alt+left', function() {
        self.resizeBox('left', true);
      });
      on('alt+right', function() {
        self.resizeBox('right', true);
      });
      on('alt+up', function() {
        self.resizeBox('up', true);
      });
      on('alt+down', function() {
        self.resizeBox('down', true);
      });

      // shift+方向键：放大字框
      on('shift+left', function() {
        self.resizeBox('left');
      });
      on('shift+right', function() {
        self.resizeBox('right');
      });
      on('shift+up', function() {
        self.resizeBox('up');
      });
      on('shift+down', function() {
        self.resizeBox('down');
      });

      // DEL：删除当前字框，ESC 放弃拖拽改动
      on('back', function() {
        self.removeBox();
      });
      on('del', function() {
        self.removeBox();
      });
      on('esc', function() {
        self.cancelDrag();
        if (self.state.edit) {
          self.showHandles(self.state.edit, self.state.editHandle);
        }
      });

      // 1~5 页面缩放
      on('1', function() {
        self.setRatio(1);
      });
      on('2', function() {
        self.setRatio(2);
      });
      on('3', function() {
        self.setRatio(3);
      });
      on('4', function() {
        self.setRatio(4);
      });
      on('5', function() {
        self.setRatio(5);
      });

      // +/- 逐级缩放，每次放大原图的50%、或缩小原图的10%
      function add() {
        if (self.data.ratio < 5) {
          self.setRatio(self.data.ratio * 1.5);
        }
      }
      function sub() {
        if (self.data.ratio > 0.5) {
          self.setRatio(self.data.ratio * 0.9);
        }
      }
      on('add', add);
      on('=', add);
      on('subtract', sub);
      on('-', sub);

      // shift + 5~9 页面缩放
      on('shift+5', function() {
        self.setRatio(0.5);
      });
      on('shift+6', function() {
        self.setRatio(0.6);
      });
      on('shift+7', function() {
        self.setRatio(0.7);
      });
      on('shift+8', function() {
        self.setRatio(0.8);
      });
      on('shift+9', function() {
        self.setRatio(0.9);
      });

      // <、>: 在高亮字框中跳转
      on(',', function() {
        self.switchNextHighlightBox(-1);
      });
      on('.', function() {
        self.switchNextHighlightBox(1);
      });

      // ctrl + 1~6 高亮显示：所有、大框、小框、窄框、扁框、重叠
      on('ctrl+1', function() {
        self.switchHighlightBoxes('all');
      });
      on('ctrl+2', function() {
        self.switchHighlightBoxes('large');
      });
      on('ctrl+3', function() {
        self.switchHighlightBoxes('small');
      });
      on('ctrl+4', function() {
        self.switchHighlightBoxes('narrow');
      });
      on('ctrl+5', function() {
        self.switchHighlightBoxes('flat');
      });
      on('ctrl+6', function() {
        self.switchHighlightBoxes('overlap');
      });

      // insert/n 增加字框
      on('insert', function() {
        self.addBox();
      });
      on('n', function() {
        self.addBox();
      });
    },

    switchHighlightBoxes: function(type) {
      if (this.data.hlType === type) {
        this.data.hlType = null;
        this.clearHighlight();
      } else {
        this.data.hlType = type;
        this.highlightBoxes(type);
      }
    },

    switchNextHighlightBox: function(relative) {
      var self = this, cid = self.getCurrentCharID();
      var n = (self.data.highlight || []).length;
      if (n > 0 && n < self.data.chars.length) {
        var item = self.data.highlight.filter(function(el) {
          return el.data('highlight') === cid;
        })[0];
        var index = self.data.highlight.indexOf(item);
        var el = self.data.highlight[index < 0 ? 0 : (index + relative + n) % n];
        return self.switchCurrentBox(el.data('highlight'));
      }
    }
  });
}());
