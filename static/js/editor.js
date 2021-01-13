/**
 * Created on 2019/11/25.
 */
function initEditor(id, html) {
  UM.getEditor(id, {
    toolbarTopOffset: 10000,
    initialFrameWidth: '100%',
    onready: function () {
      if (html) {
        this.setContent(html);
      }
      else if (id !== 'content-editor') {
        this.focus();
      }
      $(this.container).css('z-index', 0);
      this.addInputRule(function (root) {
        $.each(root.getNodesByTagName('a'), function (i, a) {
          let href = a.getAttr('href');
          if (/^http/.test(href) && window.location.href.indexOf(href.replace(/\..+$/, '')) < 0) {
            a.setAttr('target', '_blank');
          }
        });
      });
    }, filterRules: function () {
      return {
        span: function (node) {
          if (/Wingdings|Symbol/.test(node.getStyle('font-family'))) {
            return true;
          } else {
            node.parentNode.removeChild(node, true);
          }
        },
        p: function (node) {
          let listTag;
          if (node.getAttr('class') == 'MsoListParagraph') {
            listTag = 'MsoListParagraph';
          }
          node.setAttr();
          if (listTag) {
            node.setAttr('class', 'MsoListParagraph');
          }
          if (!node.firstChild()) {
            node.innerHTML(UM.browser.ie ? '&nbsp;' : '<br>');
          }
        },
        div: function (node) {
          let tmpNode, p = UM.uNode.createElement('p');
          while (tmpNode = node.firstChild()) {
            if (tmpNode.type == 'text' || !UM.dom.dtd.$block[tmpNode.tagName]) {
              p.appendChild(tmpNode);
            } else {
              if (p.firstChild()) {
                node.parentNode.insertBefore(p, node);
                p = UM.uNode.createElement('p');
              } else {
                node.parentNode.insertBefore(tmpNode, node);
              }
            }
          }
          if (p.firstChild()) {
            node.parentNode.insertBefore(p, node);
          }
          node.parentNode.removeChild(node);
        },
        //$:{}表示不保留任何属性
        br: {$: {}},
        ol: {$: {}},
        ul: {$: {}},

        dl: function (node) {
          node.tagName = 'ul';
          node.setAttr();
        },
        dt: function (node) {
          node.tagName = 'li';
          node.setAttr();
        },
        dd: function (node) {
          node.tagName = 'li';
          node.setAttr();
        },
        li: function (node) {
          let className = node.getAttr('class');
          if (!className || !/list\-/.test(className)) {
            node.setAttr();
          }
          let tmpNodes = node.getNodesByTagName('ol ul');
          UM.utils.each(tmpNodes, function (n) {
            node.parentNode.insertAfter(n, node);
          });
        },
        table: function (node) {
          UM.utils.each(node.getNodesByTagName('table'), function (t) {
            UM.utils.each(t.getNodesByTagName('tr'), function (tr) {
              let p = UM.uNode.createElement('p'), child, html = [];
              while (child = tr.firstChild()) {
                html.push(child.innerHTML());
                tr.removeChild(child);
              }
              p.innerHTML(html.join('&nbsp;&nbsp;'));
              t.parentNode.insertBefore(p, t);
            });
            t.parentNode.removeChild(t);
          });
          let val = node.getAttr('width');
          node.setAttr();
          if (val) {
            node.setAttr('width', val);
          }
        },
        tbody: {$: {}},
        caption: {$: {}},
        th: {$: {}},
        td: {$: {valign: 1, align: 1, rowspan: 1, colspan: 1, width: 1, height: 1}},
        tr: {$: {}},
        h3: {$: {}},
        h2: {$: {}},
        //黑名单，以下标签及其子节点都会被过滤掉
        '-': 'script style meta iframe embed object'
      }
    }()
  });
}
