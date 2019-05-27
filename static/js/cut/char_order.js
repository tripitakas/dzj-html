/*
 * char_order.js
 *
 * Date: 2019-05-26
 * global $
 */
(function () {
  'use strict';

  var data = $.cut.data;
  var state = $.cut.state;
  var links = {};
  var paths = [];
  var linkState = {
    normalWidth: 2, curColWidth: 3, curLinkWidth: 5,
    draggingHandle: null,
    handle: null,
    avgLen: 0
  };
  var getDistance = $.cut.getDistance;

  function buildArrayLink(fromPt, toPt, tol, c1, c2, colId, color) {
    var link = data.paper.path('M' + fromPt.x + ',' + fromPt.y + 'L' + toPt.x + ',' + toPt.y)
        .initZoom().setAttr({
          stroke: color,
          'stroke-opacity': 0.9,
          'stroke-width': linkState.normalWidth / data.ratioInitial,
          'stroke-dasharray': fromPt.y < toPt.y - tol ? '' : '.'
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
    return $.cut.getHandle(char.shape, 8);
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
    var minPath = {dist: 1e5, path: null};
    paths.forEach(function (link) {
      var dist = pointToSegmentDistance(pt, link.data('fromPt'), link.data('toPt'));

      if (minPath.dist > dist && dist < linkState.avgLen) {
        minPath.dist = dist;
        minPath.path = link;
      }
    });
    return minPath.path;
  }

  function mouseHover(pt) {
    if (linkState.draggingHandle) {
      return;
    }

    var link = hitTestLink(pt);
    var lastColId = linkState.colId;
    var lastLink = linkState.link;
    var linkText;

    if (link) {
      linkState.atStart = getDistance(pt, link.data('fromPt')) < getDistance(pt, link.data('toPt'));
      linkState.handlePt = link.data(linkState.atStart ? 'fromPt' : 'toPt');
      linkText = (linkState.atStart ? '*' : '') + link.data('cid1').replace(linkState.colId, '')
          + '->' + (linkState.atStart ? '' : '*') + link.data('cid2').replace(linkState.colId, '');
    }
    if (linkState.link !== link) {
      linkState.link = link;
      linkState.colId = link && link.data('colId') || '';

      if (lastLink) {
        lastLink.setAttr({'stroke-width': linkState.curColWidth / data.ratioInitial, 'stroke-opacity': 0.9});
      }
      if (linkState.colId !== lastColId) {
        paths.forEach(function (p) {
          if (p.data('colId') === lastColId) {
            p.setAttr({'stroke-width': linkState.normalWidth / data.ratioInitial});
          }
          if (p.data('colId') === linkState.colId) {
            p.setAttr({'stroke-width': linkState.curColWidth / data.ratioInitial});
          }
        });
      }
      if (link) {
        link.setAttr({'stroke-width': linkState.curLinkWidth / data.ratioInitial, 'stroke-opacity': 0.5});
      }
    }
    createHandle('handle', linkState.handlePt);

    $('#info > .col-info').text(linkState.colId ? '栏: ' + linkState.colId : '');
    $('#info > .char-info').text(linkText ? '字: ' + linkText : '');
  }

  function mouseDown(pt) {
    if (linkState.handle) {
      linkState.handle.attr({'stroke-opacity': 0.3});
      linkState.link.attr({'stroke-opacity': 0.3});
    }
    mouseDrag(pt);
  }

  function mouseDrag(pt) {
    if (linkState.link) {
      createHandle('draggingHandle', pt);
      if (linkState.dynLink) {
        linkState.dynLink.remove();
      }
      linkState.dynLink = buildArrayLink(
          linkState.atStart ? pt : linkState.link.data('fromPt'),
          linkState.atStart ? linkState.link.data('toPt') : pt,
          10, null, null, null, '#f00');
      linkState.dynLink.setAttr({'stroke-width': linkState.curLinkWidth / data.ratioInitial, 'stroke-opacity': 0.7});
    }
  }

  function mouseUp() {
    if (linkState.draggingHandle) {
      linkState.draggingHandle.remove();
      delete linkState.draggingHandle;
      linkState.dynLink.remove();
      delete linkState.dynLink;
    }
    if (linkState.handle) {
      linkState.handle.attr({'stroke-opacity': 1})
    }
  }

  function createHandle(name, pt) {
    if (linkState[name]) {
      linkState[name].remove();
      delete linkState[name];
    }
    if (linkState.link && pt) {
      linkState[name] = data.paper.circle(pt.x, pt.y, 3.5);
    }
  }

  $.extend($.cut, {
    removeCharOrderLinks: function () {
      paths.forEach(function (link) {
        link.remove();
      });
      links = {};
      paths = [];
    },

    addCharOrderLinks: function () {
      this.removeCharOrderLinks();
      state.mouseHover = mouseHover;
      state.mouseDown = mouseDown;
      state.mouseDrag = mouseDrag;
      state.mouseUp = mouseUp;

      data.chars.forEach(function (box) {
        var nums = (box.char_id || '').split('c');
        if (box.shape && nums.length === 3) {
          var colId = nums.slice(0, 2).join('c');
          var column = links[colId] = links[colId] || [];
          column.push([parseInt(nums[2]), box]);
        }
      });
      Object.keys(links).forEach(function (colId, colIndex) {
        var column = links[colId] = links[colId].sort(function (a, b) {
          return a[0] - b[0];
        }).map(function (a) {
          return {char: a[1], link: null};
        });

        linkState.avgLen = 0;
        column.forEach(function (c, i) {
          if (i > 0) {
            var h = Math.min(getHeight(column[i - 1].char), getHeight(c.char));
            var fromPt = getCenter(column[i - 1].char);
            var toPt = getCenter(c.char);

            linkState.avgLen += getDistance(fromPt, toPt);
            c.link = buildArrayLink(fromPt, toPt, h / 4, column[i - 1].char, c.char, colId, colIndex % 2 ? '#00f' : '#07f');
            paths.push(c.link);
          }
        });
        if (linkState.avgLen) {
          linkState.avgLen /= column.length - 1;
        }
      });
    }
  });

}());
