(function () {
  'use strict';

  $.extend($.box, {
    bindKey: function (key, func) {
      $.mapKey(key, func, {direction: 'down'});
    },
    bindKeys: function () {
      let self = this;
      let on = self.bindKey;

      on('h', () => $('#help').click());
      on('p', () => $('#toggle-image').click());
      on('b', () => $('#toggle-blur').click());
      on('+', () => self.zoomImg(self.data.ratio * 1.2));
      on('=', () => self.zoomImg(self.data.ratio * 1.2));
      on('-', () => self.zoomImg(self.data.ratio * 0.9));
      on('v', () => $('#toggle-multi').click());

      on('a', () => $.box.cStatus.isMulti ? $.box.moveBox('left') : $('#toggle-white').click());
      on('s', () => $.box.cStatus.isMulti ? $.box.moveBox('down') : $('#toggle-opacity').click());
      on('d', () => $.box.cStatus.isMulti ? $.box.moveBox('right') : $('#toggle-overlap').click());
      on('f', () => self.isCutMode() ? $('#toggle-mayWrong').click() : $('#toggle-back-box').click());
      on('q', () => $('#toggle-large').click());
      on('w', () => $.box.cStatus.isMulti ? $.box.moveBox('up') : $('#toggle-small').click());
      on('e', () => self.isCutMode() ? $('#toggle-narrow').click() : $('#toggle-link-char').click());
      on('r', () => $('#toggle-flat').click());
      on('c', () => $.box.isCutMode() ? $('#btn-check-cut').click() : $('#btn-check-link').click());

      on('i', () => $('#toggle-my-hint').click());
      on('l', () => $('#op-hint').click());
      on('esc', () => $('#no-hint').click());
      on('t', () => $('#task-submit').click());
      on('y', () => $('#task-submit-back').click());
      on('u', () => $('#save').click());
      on('k', () => $('#task-return').click());
      on('m', () => $('#toggle-order').click());
      on('n', () => $('#toggle-cut').click());
      on(',', () => $('#task-prev').click());
      on('.', () => $('#task-next').click());

      on('back', () => self.isCutMode() ? self.deleteBox() : self.switchCurBox(self.deleteCurLink()));
      on('del', () => self.isCutMode() ? self.deleteBox() : self.switchCurBox(self.deleteCurLink()));
      on('x', () => self.isCutMode() ? self.deleteBox() : self.switchCurBox(self.deleteCurLink()));

      on('left', () => self.navigate('left'));
      on('right', () => self.navigate('right'));
      on('up', () => self.navigate('up'));
      on('down', () => self.navigate('down'));

      on('alt+left', () => self.resizeBox('left', false));
      on('alt+right', () => self.resizeBox('right', false));
      on('alt+up', () => self.resizeBox('up', false));
      on('alt+down', () => self.resizeBox('down', false));
      on('shift+left', () => self.resizeBox('left', true));
      on('shift+right', () => self.resizeBox('right', true));
      on('shift+up', () => self.resizeBox('up', true));
      on('shift+down', () => self.resizeBox('down', true));

      on('g', () => self.isCutMode() && self.redo());
      on('j', () => self.isCutMode() && self.undo());

      on('1', () => self.zoomImg(1));
      on('2', () => self.zoomImg(2));
      on('3', () => self.zoomImg(3));
      on('4', () => self.zoomImg(4));
      on('5', () => self.zoomImg(5));
      on('6', () => self.zoomImg(0.6));
      on('7', () => self.zoomImg(0.7));
      on('8', () => self.zoomImg(0.8));
      on('9', () => self.zoomImg(0.9));
    },
  });
  $.box.bindKeys();
}());