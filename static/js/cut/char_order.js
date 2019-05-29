/*
 * char_order.js
 *
 * Date: 2019-05-29
 * global $
 */
(function () {
  'use strict';

  var data = $.cut.data;
  var state = $.cut.state;
  var colChars = {};    // 每列的字框 {colId: [[char_no, box]...]
  var colLinks = [];    // 字框连线
  var texts = [];       // 字框编号文本图形
  var colPaths = {};    // 每列的连通线
  var linkData = {
    normalWidth: 2, curColWidth: 3, curLinkWidth: 6,
    draggingHandle: null,
    curHandle: null,
    avgLen: 0,
    textVisible: false
  };
  var getDistance = $.cut.getDistance;

  function round(num) {
    return Math.round(num * 100) / 100;
  }

  function buildArrayLink(fromPt, toPt, tol, c1, c2, colId, color) {
    var path = 'M' + round(fromPt.x) + ',' + round(fromPt.y) + 'L' + round(toPt.x) + ',' + round(toPt.y);
    var link = data.paper.path(path)
        .initZoom().setAttr({
          stroke: color,
          'stroke-opacity': 0.9,
          'stroke-width': linkData.normalWidth / data.ratioInitial,
          'stroke-dasharray': fromPt.y < toPt.y - tol ? '' : '.'    // 向上或水平就显示虚线，否则为实线
        })
        .data('fromPt', fromPt)
        .data('toPt', toPt);

    if (c1 && c2) {
      link.data('c1', c1)
          .data('c2', c2)
          .data('colId', colId)
          .data('cid1', c1.shape.data('cid'))
          .data('cid2', c2.shape.data('cid'));
    }
    return link;
  }

  function getCenter(char) {
    return $.cut.getHandle(char && char.shape || char, 8);
  }

  function getHeight(char) {
    var box = char.shape.getBBox();
    return box.height;
  }

  function pointToSegmentDistance(pt, pa, pb) {
    var a = getDistance(pt, pa), b = getDistance(pt, pb), c = getDistance(pa, pb);

    if (a < 1e-4 || b < 1e-4) {
      return 0;
    }
    if (c < 1e-4) {
      return a;
    }

    // 钝角、直角三角形: 返回到端点的距离
    if (a * a >= b * b + c * c) {
      return b;
    }
    if (b * b >= a * a + c * c) {
      return a;
    }

    // 海伦公式，锐角三角形
    var l = (a + b + c) / 2;
    var s = Math.sqrt(l * (l - a) * (l - b) * (l - c));
    return 2 * s / c;
  }

  function hitTestLink(pt) {
    var minDist = 1e5, minPath = null;
    colLinks.forEach(function (link) {
      var dist = pointToSegmentDistance(pt, link.data('fromPt'), link.data('toPt'));
      var diff = link === linkData.link ? 10 : 0;  // 当前连线段优先捕捉

      if (minDist > dist - diff && dist < linkData.avgLen) {
        minDist = dist - diff;
        minPath = link;
      }
    });
    return minPath;
  }

  function onColChanged(link, lastColId) {
    function run() {
      if (colChars[linkData.colId]) {
        var ms = 150 * colChars[linkData.colId].length;
        linkData.alongBall.animate({along: 1}, ms, function () {
          linkData.alongBall.attr({along: 0});
          setTimeout(run);
        });
      }
    }

    colLinks.forEach(function (p) {
      if (p.data('colId') === lastColId) {
        p.setAttr({'stroke-width': linkData.normalWidth / data.ratioInitial});
      }
      if (p.data('colId') === linkData.colId && p !== link) {
        p.setAttr({'stroke-width': linkData.curColWidth / data.ratioInitial});
      }
    });
    if (linkData.alongBall) {
      linkData.alongBall.remove();
    }
    var alongPath = colPaths[linkData.colId];
    if (alongPath) {
      linkData.alongLen = alongPath.getTotalLength();
      linkData.alongBall = data.paper.circle(0, 0, 2).attr({stroke: '#f00', fill: '#fff'});

      data.paper.customAttributes.along = function (v) {
        var point = alongPath.getPointAtLength(v * linkData.alongLen);
        return point && {transform: "t" + [point.x, point.y] + "r" + point.alpha};
      };
      linkData.alongBall.attr({along: 0});

      setTimeout(run);
    }
  }

  function mouseHover(pt) {
    if (linkData.draggingHandle) {
      return;
    }

    var link = hitTestLink(pt);
    var lastColId = linkData.colId;
    var lastLink = linkData.link;
    var lastStart = linkData.atStart;
    var linkText, handleChanged;

    if (link) {
      linkData.atStart = getDistance(pt, link.data('fromPt')) < getDistance(pt, link.data('toPt'));
      linkData.handlePt = link.data(linkData.atStart ? 'fromPt' : 'toPt');
      linkText = (linkData.atStart ? '*' : '') + link.data('cid1').replace(linkData.colId, '')
          + '->' + (linkData.atStart ? '' : '*') + link.data('cid2').replace(linkData.colId, '');
    }
    handleChanged = linkData.link !== link || lastStart !== linkData.atStart;
    if (linkData.link !== link) {
      linkData.link = link;
      linkData.colId = link && link.data('colId') || '';

      if (lastLink) {
        lastLink.setAttr({'stroke-width': linkData.curColWidth / data.ratioInitial, 'stroke-opacity': 0.9});
      }
      if (linkData.colId !== lastColId) {
        onColChanged(link, lastColId);
      }
      if (link) {
        link.setAttr({'stroke-width': linkData.curLinkWidth / data.ratioInitial, 'stroke-opacity': 0.8});
      }
    }
    createHandle('curHandle', linkData.handlePt,
        link && link.data(linkData.atStart ? 'cid1' : 'cid2'), handleChanged);

    $('#info > .col-info').text(linkData.colId ? '栏: ' + linkData.colId : '');
    $('#info > .char-info').text(linkText ? '字: ' + linkText : '');
  }

  function mouseDown(pt) {
    if (linkData.curHandle) {
      linkData.curHandle.attr({'stroke-opacity': 0.2});
      linkData.link.attr({'stroke-opacity': 0.2});
    }
    mouseDrag(pt);
  }

  function mouseDrag(pt) {
    if (linkData.link) {
      linkData.dragTarget = $.cut.findBoxByPoint(pt);
      if (linkData.dragTarget) {
        pt = getCenter(linkData.dragTarget);
      }
      $('#info > .target-char').text(linkData.dragTarget ?
          linkData.dragTarget.data('cid').replace(linkData.colId, '') : '');

      createHandle('draggingHandle', pt, linkData.dragTarget && linkData.dragTarget.data('cid'));
      if (linkData.dynLink) {
        linkData.dynLink.remove();
      }
      var startPt = linkData.atStart ? pt : linkData.link.data('fromPt');
      var toPt = linkData.atStart ? linkData.link.data('toPt') : pt;
      linkData.dynLink = buildArrayLink(startPt, toPt, 10, null, null, null, '#f00');
      linkData.dynLink.setAttr({
        'stroke-width': linkData.curLinkWidth / data.ratioInitial,
        'stroke-opacity': 0.7
      });
    }
  }

  // 直接拖动就将目标字框插入当前列，拖到空白处就原字框解除连接
  // pickTarget: 改连接到目标字框上，原字框解除连接
  // insertTarget: 将目标字框插入当前列，原字框不变，目标字框分配新号（整列重排编号）
  function onLinkChanged(charOld, charNew, pickTarget, insertTarget) {
    var t, chars, index;

    if (insertTarget && linkData.dragTarget) {
      chars = data.chars.filter(function (box) {
        if (box !== charNew && box.char_id && box.char_id.indexOf(linkData.colId + 'c') === 0) {
          box.char_no = parseInt(box.char_id.replace(linkData.colId + 'c', ''));
          return true;
        }
      }).sort(function (a, b) {
        return a.char_no - b.char_no;
      });
      index = chars.indexOf(charOld);
      console.assert(index >= 0);

      if (charNew) {
        chars.splice(index, 0, charNew);
        charNew.block_no = charOld.block_no;
        charNew.line_no = charOld.line_no;
      }
      chars.forEach(function (box, i) {
        box.char_no = box.no = i + 1;
        box.char_id = 'b' + box.block_no + 'c' + box.line_no + 'c' + box.char_no;
        box.shape.data('cid', box.char_id);
      });
    } else {
      ['block_no', 'line_no', 'char_no', 'no', 'char_id'].forEach(function (f) {
        if (!linkData.dragTarget || !charNew) {
          charOld[f] = null;
        } else {
          t = charOld[f];
          charOld[f] = pickTarget ? null : charNew[f];
          charNew[f] = t;
        }
      });
      if (pickTarget || !linkData.dragTarget) {
        for (t = 1; t < 1000 && $.cut.findCharById('break' + t);) t++;
        charOld.char_id = 'break' + t;
      }
      charOld.shape.data('cid', charOld.char_id);
      if (charNew) {
        charNew.shape.data('cid', charNew.char_id);
      }
    }

    $.cut.undoData.change();
    $.cut.notifyChanged(charNew && charNew.shape, 'changed');
  }

  function mouseUp(pt, e) {
    if (linkData.draggingHandle) {
      var cidNew = linkData.draggingHandle.data('cid');
      var cidOld = linkData.curHandle.data('cid');
      var charOld = $.cut.findCharById(cidOld);
      var charNew = $.cut.findCharById(cidNew);

      linkData.draggingHandle.remove();
      delete linkData.draggingHandle;
      linkData.dynLink.remove();
      delete linkData.dynLink;

      // 直接拖动就将目标字框插入当前列，按下shift键拖动就改连接到目标字框上，原字框解除连接，按下alt键拖动就交换字框编号
      if (charOld && (charNew && cidNew !== cidOld || !linkData.dragTarget)) {
        onLinkChanged(charOld, charNew, e.shiftKey, !e.altKey && !e.shiftKey);
        setTimeout(function () {
          $.cut.addCharOrderLinks();
        }, 500);
      }
      if (linkData.dragTarget) {
        $('#info > .target-char').text('');
      }
    }
    if (linkData.curHandle) {
      linkData.curHandle.attr({'stroke-opacity': 1})
    }
  }

  function createHandle(name, pt, cid, switched) {
    var r = cid ? 5 : 10;
    if (linkData[name] && !pt) {
      linkData[name].remove();
      delete linkData[name];
    }
    if (linkData[name] && pt) {
      linkData[name].animate({cx: pt.x, cy: pt.y, r: r}, 300, 'elastic');
    }
    else if (linkData.link && pt) {
      linkData[name] = data.paper.circle(pt.x, pt.y, switched ? 8 : r)
          .attr({fill: 'rgba(0,255,0,.4)'});
      if (switched) {
        linkData[name].animate({r: r}, 1000, 'elastic');
      }
    }
    if (linkData[name]) {
      linkData[name].data('cid', cid);
    }
  }

  $.extend($.cut, {
    removeCharOrderLinks: function () {
      delete linkData.colId;

      colLinks.forEach(function (link) {
        link.remove();
      });
      colChars = {};
      colLinks.length = 0;

      texts.forEach(function (text) {
        text.remove();
      });
      texts = [];

      Object.keys(colPaths).forEach(function (id) {
        colPaths[id].remove();
      });
      colPaths = {};

      if (linkData.curHandle) {
        linkData.curHandle.remove();
        delete linkData.curHandle;
      }
      if (linkData.draggingHandle) {
        linkData.draggingHandle.remove();
        delete linkData.draggingHandle;
      }
    },

    addCharOrderLinks: function () {
      state.mouseHover = mouseHover;
      state.mouseDown = mouseDown;
      state.mouseDrag = mouseDrag;
      state.mouseUp = mouseUp;

      this.removeCharOrderLinks();
      data.chars.forEach(function (box) {
        var nums = (box.char_id || '').split('c');
        if (box.shape && nums.length === 3) {
          var colId = nums.slice(0, 2).join('c');
          colChars[colId] = colChars[colId] || [];
          colChars[colId].push([parseInt(nums[2]), box]);
          if (linkData.textVisible) {
            var cen = getCenter(box);
            texts.push(data.paper.text(cen.x, cen.y, nums.slice(1, 3).join('c'))
                .attr({'font-size': '13px'}));
          }
        }
      });

      Object.keys(colChars).forEach(function (colId, colIndex) {
        var column = colChars[colId] = colChars[colId].sort(function (a, b) {
          return a[0] - b[0];
        }).map(function (a) {
          return {char: a[1], link: null};
        });

        var avgLen = 0;
        var points = [getCenter(column[0].char)];
        column.forEach(function (c, i) {
          if (i > 0) {
            var h = Math.min(getHeight(column[i - 1].char), getHeight(c.char));
            var fromPt = getCenter(column[i - 1].char);
            var toPt = getCenter(c.char);

            avgLen += getDistance(fromPt, toPt);
            c.link = buildArrayLink(fromPt, toPt, h / 4,
                column[i - 1].char, c.char, colId, colIndex % 2 ? '#00f' : '#07f');
            colLinks.push(c.link);
            points.push(toPt);
          }
        });
        linkData.avgLen = avgLen && avgLen / (column.length - 1);
        colPaths[colId] = data.paper.path(points.map(function (pt, i) {
          return (i > 0 ? 'L' : 'M') + round(pt.x) + ',' + round(pt.y);
        }).join(' ')).attr({stroke: 'none'});
      });
    }
  });

  // 放缩后重新生成图形
  state.onZoomed = function () {
    if (colLinks.length) {
      $.cut.addCharOrderLinks();
    }
  };

  // Undo/Redo后重新生成图形
  $.cut.onBoxChanged(function(info, box, reason) {
    if (colLinks.length && reason === 'undo') {
      $.cut.addCharOrderLinks();
    }
  });

  // 显隐字框编号
  $('#switch-char-no').click(function () {
    linkData.textVisible = !linkData.textVisible;
    $.cut.addCharOrderLinks();
  });

}());
