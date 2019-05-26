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
  var linkState = {normalWidth: 2, currentWidth: 4, avgLen: 0};

  function buildArrayLink(fromPt, toPt, tol, c1, c2, colId, color) {
    return data.paper.path('M' + fromPt.x + ',' + fromPt.y + 'L' + toPt.x + ',' + toPt.y)
        .initZoom().setAttr({
          stroke: color,
          'stroke-opacity': 0.9,
          'stroke-width': linkState.normalWidth / data.ratioInitial,
          'stroke-dasharray': fromPt.y < toPt.y - tol ? '' : '.'
        })
        .data('fromPt', fromPt)
        .data('toPt', toPt)
        .data('cid1', c1.shape.data('cid'))
        .data('cid2', c2.shape.data('cid'))
        .data('colId', colId);
  }

  function getCenter(char) {
    return $.cut.getHandle(char.shape, 8);
  }

  function getHeight(char) {
    var box = char.shape.getBBox();
    return box.height;
  }

  function hitTestLink(pt) {
    var minPath = {dist: 1e5, path: null};
    paths.forEach(function (link) {
      var fromPt = link.data('fromPt'), toPt = link.data('toPt');
      var cenDist = $.cut.getDistance(pt, {x: (fromPt.x + toPt.x) / 2, y: (fromPt.y + toPt.y) / 2});
      var fromDist = $.cut.getDistance(pt, fromPt);
      var toDist = $.cut.getDistance(pt, toPt);
      var dist = Math.min(fromDist, toDist) + cenDist;

      if (minPath.dist > dist && dist < linkState.avgLen) {
        minPath.dist = dist;
        minPath.path = link;
      }
    });
    return minPath.path;
  }

  function mouseHover(pt) {
    if (linkState.dragging) {
      return;
    }

    var link = hitTestLink(pt);
    var lastColId = linkState.colId;
    var linkText, atStart;

    if (link) {
      atStart = $.cut.getDistance(pt, link.data('fromPt')) < $.cut.getDistance(pt, link.data('toPt'));
      linkText = (atStart ? '*' : '') + link.data('cid1') + '->' + (atStart ? '' : '*') + link.data('cid2');
    }
    if (linkState.link !== link) {
      linkState.link = link;
      linkState.colId = link && link.data('colId') || '';
      if (linkState.colId !== lastColId) {
        paths.forEach(function (p) {
          if (p.data('colId') === lastColId) {
            p.setAttr({'stroke-width': linkState.normalWidth / data.ratioInitial});
          }
          if (p.data('colId') === linkState.colId) {
            p.setAttr({'stroke-width': linkState.currentWidth / data.ratioInitial});
          }
        });
      }
      $('#info > .col-info').text(linkState.colId ? '栏: ' + linkState.colId : '');
      $('#info > .char-info').text(linkText ? '字: ' + linkText : '');
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

            linkState.avgLen += $.cut.getDistance(fromPt, toPt);
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
