(function () {
  'use strict';

  $.extend($.box, {
    isMode: function (mode) {
      return this.status.boxMode === mode;
    },
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
      on('c', () => $('#btn-check').click());
      on('z', () => {
        self.isMode('cut') && self.undo();
      });
      on('v', () => {
        self.isMode('cut') && self.redo();
      });

      // 任务与步骤
      on('t', () => {
        if (self.isMode('order')) $('#task-submit').click();
      });
      on('y', () => {
        if (self.isMode('order')) $('#task-submit-back').click();
      });
      on('ctrl+s', () => {
        $('#save').click();
      });
      on('ctrl+r', () => {
        $('#task-return').click();
      });
      on('.', () => {
        if (self.isMode('order')) $('#toggle-cut').click();
      });
      on('/', () => {
        if (self.isMode('cut')) $('#toggle-order').click();
      });
      on(']', () => {
        $('#task-next').click();
      });
      on('[', () => {
        $('#task-prev').click();
      });

      // 图片操作
      on('m', () => $('#toggle-blur').click());
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
        if (self.isMode('cut'))
          self.cStatus.isMulti ? self.moveBox('left') : $('#toggle-white').click();
      });
      on('s', () => {
        if (self.isMode('cut'))
          self.cStatus.isMulti ? self.moveBox('down') : $('#toggle-opacity').click();
      });
      on('d', () => {
        if (self.isMode('cut'))
          self.cStatus.isMulti ? self.moveBox('right') : $('#toggle-overlap').click();
      });
      on('f', () => {
        if (self.isMode('cut')) $('#toggle-mayWrong').click();
      });
      on('q', () => {
        if (self.isMode('cut')) $('#toggle-large').click();
      });
      on('w', () => {
        if (self.isMode('cut'))
          self.cStatus.isMulti ? self.moveBox('up') : $('#toggle-small').click();
      });
      on('e', () => {
        if (self.isMode('cut')) $('#toggle-narrow').click();
      });
      on('r', () => {
        if (self.isMode('cut')) $('#toggle-flat').click();
      });

      // 框操作
      on('l', () => {
        $('#toggle-block').click();
      });
      on('k', () => {
        $('#toggle-column').click();
      });
      on('j', () => {
        $('#toggle-char').click();
      });
      on("o", () => {
        if (self.isMode('cut')) $('#toggle-image').click();
      });
      on(";", () => {
        if (self.isMode('cut')) $('#toggle-all').click();
      });
      on("ctrl+v", () => {
        if (self.isMode('cut')) $.box.copyBox();
      });
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
        self.isMode('cut') ? self.deleteBox() : self.switchCurBox(self.deleteCurLink());
      });
      on('n', () => {
        $('#toggle-no-char').click();
      });
      on('i', () => {
        if (self.isMode('cut')) $('#toggle-my-hint').click();
      });
      on('g', () => {
        if (self.isMode('cut')) $('#toggle-multi').click();
      });
      on('space', () => {
        if (self.isMode('cut') && self.cStatus.isMulti)
          self.toggleClass(self.status.curBox, 'u-selected');
      });
      on('left', () => {
        let navType = self.isMode('cut') ? self.status.curBoxType : self.oStatus.curLinkType;
        self.navigate('left', navType);
      });
      on('right', () => {
        let navType = self.isMode('cut') ? self.status.curBoxType : self.oStatus.curLinkType;
        self.navigate('right', navType);
      });
      on('up', () => {
        let navType = self.isMode('cut') ? self.status.curBoxType : self.oStatus.curLinkType;
        self.navigate('up', navType);
      });
      on('down', () => {
        let navType = self.isMode('cut') ? self.status.curBoxType : self.oStatus.curLinkType;
        self.navigate('down', navType);
      });

      on('alt+left', () => {
        if (self.isMode('cut')) self.resizeBox('left', false);
      });
      on('alt+right', () => {
        if (self.isMode('cut')) self.resizeBox('right', false);
      });
      on('alt+up', () => {
        if (self.isMode('cut')) self.resizeBox('up', false);
      });
      on('alt+down', () => {
        if (self.isMode('cut')) self.resizeBox('down', false);
      });
      on('shift+left', () => {
        if (self.isMode('cut')) self.resizeBox('left', true);
      });
      on('shift+right', () => {
        if (self.isMode('cut')) self.resizeBox('right', true);
      });
      on('shift+up', () => {
        if (self.isMode('cut')) self.resizeBox('up', true);
      });
      on('shift+down', () => {
        if (self.isMode('cut')) self.resizeBox('down', true);
      });

      // 序操作
      on('u', () => {
        if (self.isMode('order')) $('#toggle-link-char').click();
      });

    },
  });

  $.box.bindKeys();

}());