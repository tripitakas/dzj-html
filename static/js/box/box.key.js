(function () {
  'use strict';

  $.extend($.box, {
    bindKey: function (key, func) {
      $.mapKey(key, func, {direction: 'down'});
    },
    bindKeys: function () {
      let self = this;
      let on = self.bindKey;

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
      on('a', function () {
        self.moveBox('left');
      });
      on('d', function () {
        self.moveBox('right');
      });
      on('w', function () {
        self.moveBox('up');
      });
      on('s', function () {
        self.moveBox('down');
      });

      // alt+方向键：缩小字框
      on('alt+left', function () {
        self.resizeBox('left', false);
      });
      on('alt+right', function () {
        self.resizeBox('right', false);
      });
      on('alt+up', function () {
        self.resizeBox('up', false);
      });
      on('alt+down', function () {
        self.resizeBox('down', false);
      });

      // shift+方向键：放大字框
      on('shift+left', function () {
        self.resizeBox('left', true);
      });
      on('shift+right', function () {
        self.resizeBox('right', true);
      });
      on('shift+up', function () {
        self.resizeBox('up', true);
      });
      on('shift+down', function () {
        self.resizeBox('down', true);
      });

      // back/del 删除字
      on('back', function () {
        if (self.isCutMode()) {
          self.deleteBox();
        } else {
          self.switchCurBox(self.deleteCurLink());
        }
      });
      on('del', function () {
        if (self.isCutMode()) {
          self.deleteBox();
        } else {
          self.switchCurBox(self.deleteCurLink());
        }
      });
      on('e', function () {
        if (self.isCutMode()) {
          self.deleteBox();
        } else {
          self.switchCurBox(self.deleteCurLink());
        }
      });

      // z Undo, r Redo
      on('z', function () {
        if (self.isCutMode()) self.undo();
      });
      on('r', function () {
        if (self.isCutMode()) self.undo();
      });

      // 1~5 页面缩放
      on('1', function () {
        self.zoomImg(1);
      });
      on('2', function () {
        self.zoomImg(2);
      });
      on('3', function () {
        self.zoomImg(3);
      });
      on('4', function () {
        self.zoomImg(4);
      });
      on('5', function () {
        self.zoomImg(5);
      });

      // 6~9 页面缩放
      on('6', function () {
        self.zoomImg(0.6);
      });
      on('7', function () {
        self.zoomImg(0.7);
      });
      on('8', function () {
        self.zoomImg(0.8);
      });
      on('9', function () {
        self.zoomImg(0.9);
      });

      // +/- 逐级缩放
      on('add', function () {
        self.zoomImg(self.data.ratio * 1.2);
      });
      on('=', function () {
        self.zoomImg(self.data.ratio * 1.2);
      });
      on('subtract', function () {
        self.zoomImg(self.data.ratio * 0.9);
      });
      on('-', function () {
        self.zoomImg(self.data.ratio * 0.9);
      });
    },
  });

  $.box.bindKeys();

}());