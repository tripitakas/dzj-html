(function () {
  'use strict';

  $.extend($.box, {
    isMode: function (mode) {
      return this.status.boxMode === mode;
    },
    bindKey: function (key, func) {
      if (key.trim() === ',')
        $.mapKey(',', func, {direction: 'down'});
      else key.split(',').forEach((k) => {
        $.mapKey(k.trim(), func, {direction: 'down'});
      });
    },
    bindBaseKeys: function (readonly) {
      let self = this;
      let on = self.bindKey;

      // 图片操作
      // on('h', () => $('#help').click());
      on('space', () => $('#toggle-blur').click());
      on('p', () => $('#toggle-img').click());
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

      // 框操作
      on('j', () => {
        $('#toggle-char').click();
      });
      on('k', () => {
        $('#toggle-column').click();
      });
      on('l', () => {
        $('#toggle-block').click();
      });
      on('tab', () => {
        let seqs = ['char', 'column', 'block'];
        let next = (seqs.indexOf(self.status.curBoxType) + 1) % 3;
        $(`#toggle-${seqs[next]}`).click();
      });
      on('shift+tab', () => {
        let seqs = ['char', 'column', 'block'];
        let prev = (seqs.indexOf(self.status.curBoxType) + 2) % 3;
        $(`#toggle-${seqs[prev]}`).click();
      });
      on(';', () => {
        if (self.isMode('cut')) $('#toggle-all').click();
      });
      on('n', () => {
        $('#toggle-no-char').click();
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
      if (readonly) return;
      on('back,del,x', () => {
        self.isMode('cut') ? self.deleteBox() : self.switchCurBox(self.deleteCurLink());
      });
      on('ctrl+v', () => {
        if (self.isMode('cut') && !$.box.status.isMulti) $.box.copyBox();
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
    },

    bindFullKeys: function () {
      let self = this;
      let on = self.bindKey;
      self.bindBaseKeys();

      // 系统操作
      on('esc', () => {
        $('#btn-reset').click();
      });
      on('c', () => $('#btn-check').click());
      on('ctrl+z', () => {
        self.isMode('cut') && self.undo();
      });
      on('ctrl+x', () => {
        self.isMode('cut') && self.redo();
      });
      on('ctrl+s', () => {
        if ($('#save').css('display') === 'block') $('#save').click();
      });

      // 切换步骤
      on('g', () => {
        if (self.isMode('order')) $('#toggle-cut').click();
      });
      on('b', () => {
        if (self.isMode('cut')) $('#toggle-order').click();
      });

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
          self.cStatus.isMulti ? self.moveBox('right') : $('#toggle-narrow').click();
      });
      on('f', () => {
        if (self.isMode('cut')) $('#toggle-flat').click();
      });
      on('q', () => {
        if (self.isMode('cut')) $('#toggle-small').click();
      });
      on('w', () => {
        if (self.isMode('cut'))
          self.cStatus.isMulti ? self.moveBox('up') : $('#toggle-large').click();
      });
      on('e', () => {
        if (self.isMode('cut')) $('#toggle-overlap').click();
      });
      on('r', () => {
        if (self.isMode('cut')) $('#toggle-mayWrong').click();
      });

      // 框操作
      on("o", () => {
        if (self.isMode('cut')) $('#toggle-image').click();
      });
      on('i', () => {
        if (self.isMode('cut')) $('#toggle-my-hint').click();
      });
      on('v', () => {
        if (self.isMode('cut')) $('#toggle-multi').click();
      });

      // 序操作
      on('u', () => {
        if (self.isMode('order')) $('#toggle-link-char').click();
      });

    },
  });

}());