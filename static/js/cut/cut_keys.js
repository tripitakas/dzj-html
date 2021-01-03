/* global $ */
(function () {
  'use strict';

  $.extend($.cut, {
    bindKey: function (key, func) {
      $.mapKey(key, func, {direction: 'down'});
    },
    bindKeys: function () {
      var self = this;
      var on = this.bindKey;

      // 方向键：在字框间导航
      on('left', function () {
        self.navigate('left');
      });
      on('right', function () {
        self.navigate('right');
      });
      on('up', function () {
        self.navigate('up');
      });
      on('down', function () {
        self.navigate('down');
      });

      // w a s d：移动当前字框
      on('shift+a', function () {
        self.moveBox('left');
      });
      on('shift+d', function () {
        self.moveBox('right');
      });
      on('shift+w', function () {
        self.moveBox('up');
      });
      on('shift+s', function () {
        self.moveBox('down');
      });

      // alt+方向键：缩小字框
      on('alt+left', function () {
        self.resizeBox('left', true);
      });
      on('alt+right', function () {
        self.resizeBox('right', true);
      });
      on('alt+up', function () {
        self.resizeBox('up', true);
      });
      on('alt+down', function () {
        self.resizeBox('down', true);
      });

      // shift+方向键：放大字框
      on('shift+left', function () {
        self.resizeBox('left');
      });
      on('shift+right', function () {
        self.resizeBox('right');
      });
      on('shift+up', function () {
        self.resizeBox('up');
      });
      on('shift+down', function () {
        self.resizeBox('down');
      });

      // DEL：删除当前字框，ESC 放弃拖拽改动
      on('back', function () {
        self.removeBox();
      });
      on('del', function () {
        self.removeBox();
      });
      on('e', function () {
        self.removeBox();
      });
      on('esc', function () {
        self.cancelDrag();
        if (self.state.edit) {
          self.showHandles(self.state.edit, self.state.editHandle);
        }
      });

      // z Undo, r Redo
      on('z', function () {
        self.undo();
      });
      on('r', function () {
        self.redo();
      });

      // 1~5 页面缩放
      on('1', function () {
        self.setRatio(1);
      });
      on('2', function () {
        self.setRatio(2);
      });
      on('3', function () {
        self.setRatio(3);
      });
      on('4', function () {
        self.setRatio(4);
      });
      on('5', function () {
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

      // 6~9 页面缩放
      on('6', function () {
        self.setRatio(0.6);
      });
      on('7', function () {
        self.setRatio(0.7);
      });
      on('8', function () {
        self.setRatio(0.8);
      });
      on('9', function () {
        self.setRatio(0.9);
      });

      // <、>: 在高亮字框中跳转
      on(',', function () {
        self.switchNextHighlightBox(-1);
      });
      on('.', function () {
        self.switchNextHighlightBox(1);
      });

      // ctrl + 1~6 高亮显示：所有、大框、小框、窄框、扁框、重叠
      on('ctrl+1', function () {
        self.switchHighlightBoxes('all');
      });
      on('ctrl+2', function () {
        self.switchHighlightBoxes('large');
      });
      on('ctrl+3', function () {
        self.switchHighlightBoxes('small');
      });
      on('ctrl+4', function () {
        self.switchHighlightBoxes('narrow');
      });
      on('ctrl+5', function () {
        self.switchHighlightBoxes('flat');
      });
      on('ctrl+6', function () {
        self.switchHighlightBoxes('overlap');
      });

      // insert/n 增加字框
      on('ctrl+v', function () {
        self.addBox();
      });
    },

    switchHighlightBoxes: function (type) {
      if (this.data.hlType === type) {
        this.data.hlType = null;
        this.clearHighlight();
      } else {
        this.data.hlType = type;
        this.highlightBoxes(type);
      }
    },

    switchNextHighlightBox: function (relative) {
      var self = this, cid = self.getCurrentCharID();
      var n = (self.data.highlight || []).length;
      if (n > 0 && n < self.data.chars.length) {
        var item = self.data.highlight.filter(function (el) {
          return el.data('highlight') === cid;
        })[0];
        var index = self.data.highlight.indexOf(item);
        var el = self.data.highlight[index < 0 ? 0 : (index + relative + n) % n];
        return self.switchCurrentBox(el.data('highlight'));
      }
    }
  });
}());


// 图片缩放快捷键
function zoomRatio(ratio) {
  var pageImg = $('#page-picture img');
  if (pageImg.length) {
    pageImg.width((100 * ratio) + '%');
  } else {
    $.cut.setRatio(ratio);
  }
}

$.mapKey('1', function () {
  zoomRatio(1);
});
$.mapKey('2', function () {
  zoomRatio(2);
});
$.mapKey('3', function () {
  zoomRatio(3);
});
$.mapKey('4', function () {
  zoomRatio(4);
});
$.mapKey('5', function () {
  zoomRatio(5);
});
$.mapKey('6', function () {
  zoomRatio(0.6);
});
$.mapKey('7', function () {
  zoomRatio(0.8);
});
$.mapKey('8', function () {
  zoomRatio(0.8);
});
$.mapKey('9', function () {
  zoomRatio(0.9);
});
