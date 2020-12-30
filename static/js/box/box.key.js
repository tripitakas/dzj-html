(function () {
  'use strict';

  $.extend($.box, {
    bindKey: function (key, func) {
      key.split(',').forEach((k) => {
        $.mapKey(k.trim(), func, {direction: 'down'});
      });
    },
    bindKeys: function () {
      let self = this;
      let on = self.bindKey;

      // 系统操作
      on('esc', () => {
        $('#btn-reset').click();
      });
      on('h', () => $('#help').click());
      on('c', () => {
        $('#btn-check').click();
      });
      on('z', () => {
        self.isCutMode() && self.undo();
      });
      on('v', () => {
        self.isCutMode() && self.redo();
      });

      // 任务与步骤
      on('t', () => {
        if (self.isOrderMode()) $('#task-submit').click();
      });
      on('y', () => {
        if (self.isOrderMode()) $('#task-submit-back').click();
      });
      on('u', () => {
        $('#save').click();
      });
      on('k', () => {
        $('#task-return').click();
      });
      on('[', () => {
        if (self.isOrderMode()) $('#toggle-cut').click();
      });

      on(']', () => {
        if (self.isCutMode()) $('#toggle-order').click();
      });

      // 图片操作
      on('o', () => $('#toggle-blur').click());
      on('p', () => $('#toggle-image').click());
      on('+', () => self.zoomImg(self.data.ratio * 1.2));
      on('=', () => self.zoomImg(self.data.ratio * 1.2));
      on('-', () => self.zoomImg(self.data.ratio * 0.9));
      on('1', () => self.zoomImg(1));
      on('2', () => self.zoomImg(2));
      on('3', () => self.zoomImg(3));
      on('4', () => self.zoomImg(4));
      on('5', () => self.zoomImg(5));
      on('6', () => self.zoomImg(0.6));
      on('7', () => self.zoomImg(0.7));
      on('8', () => self.zoomImg(0.8));
      on('9', () => self.zoomImg(0.9));

      // 框提示
      on('a', () => {
        if (self.isCutMode())
          self.cStatus.isMulti ? self.moveBox('left') : $('#toggle-white').click();
      });
      on('s', () => {
        if (self.isCutMode())
          self.cStatus.isMulti ? self.moveBox('down') : $('#toggle-opacity').click();
      });
      on('d', () => {
        if (self.isCutMode())
          self.cStatus.isMulti ? self.moveBox('right') : $('#toggle-overlap').click();
      });
      on('f', () => {
        if (self.isCutMode()) $('#toggle-mayWrong').click();
      });
      on('q', () => {
        if (self.isCutMode()) $('#toggle-large').click();
      });
      on('w', () => {
        if (self.isCutMode())
          self.cStatus.isMulti ? self.moveBox('up') : $('#toggle-small').click();
      });
      on('e', () => {
        if (self.isCutMode()) $('#toggle-narrow').click();
      });
      on('r', () => {
        if (self.isCutMode()) $('#toggle-flat').click();
      });

      // 框操作
      on('shift+a', () => {
        self.moveBox('left');
      });
      on('shift+d', () => {
        self.moveBox('right');
      });
      on('shift+w', () => {
        self.moveBox('up');
      });
      on('shift+s', () => {
        self.moveBox('down');
      });
      on('back,del,x', () => {
        self.isCutMode() ? self.deleteBox() : self.switchCurBox(self.deleteCurLink());
      });
      on('n', () => {
        $('#toggle-no-char').click();
      });
      on('i', () => {
        if (self.isCutMode()) $('#toggle-my-hint').click();
      });
      on('g', () => {
        if (self.isCutMode()) $('#toggle-multi').click();
      });
      on('space', () => {
        if (self.isCutMode() && self.cStatus.isMulti)
          self.toggleClass(self.status.curBox, 'u-selected');
      });
      on('left', () => {
        let navType = self.isCutMode() ? self.status.curBoxType : self.oStatus.curLinkType;
        self.navigate('left', navType);
      });
      on('right', () => {
        let navType = self.isCutMode() ? self.status.curBoxType : self.oStatus.curLinkType;
        self.navigate('right', navType);
      });
      on('up', () => {
        let navType = self.isCutMode() ? self.status.curBoxType : self.oStatus.curLinkType;
        self.navigate('up', navType);
      });
      on('down', () => {
        let navType = self.isCutMode() ? self.status.curBoxType : self.oStatus.curLinkType;
        self.navigate('down', navType);
      });

      on('alt+left', () => {
        if (self.isCutMode()) self.resizeBox('left', false);
      });
      on('alt+right', () => {
        if (self.isCutMode()) self.resizeBox('right', false);
      });
      on('alt+up', () => {
        if (self.isCutMode()) self.resizeBox('up', false);
      });
      on('alt+down', () => {
        if (self.isCutMode()) self.resizeBox('down', false);
      });
      on('shift+left', () => {
        if (self.isCutMode()) self.resizeBox('left', true);
      });
      on('shift+right', () => {
        if (self.isCutMode()) self.resizeBox('right', true);
      });
      on('shift+up', () => {
        if (self.isCutMode()) self.resizeBox('up', true);
      });
      on('shift+down', () => {
        if (self.isCutMode()) self.resizeBox('down', true);
      });

      // 序操作
      on('l', () => {
        if (self.isOrderMode()) $('#toggle-link-char').click();
      });
      on('b', () => {
        if (self.isOrderMode()) $('#toggle-back-box').click();
      });


    },
  });

  $.box.bindKeys();

}());