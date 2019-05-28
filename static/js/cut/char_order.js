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
  var links = {};
  var paths = [];
  var texts = [];
  var colPaths = {};
  var linkState = {
    normalWidth: 2, curColWidth: 3, curLinkWidth: 6,
    draggingHandle: null,
    handle: null,
    avgLen: 0,
    textVisible: false
  };
  var getDistance = $.cut.getDistance;

  function round(num) {
    return Math.round(num * 100) / 100;
  }

  function buildArrayLink(fromPt, toPt, tol, c1, c2, colId, color) {
    var link = data.paper.path('M' + round(fromPt.x) + ',' + round(fromPt.y) + 'L' + round(toPt.x) + ',' + round(toPt.y))
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
    var minPath = {dist: 1e5, path: null};
    paths.forEach(function (link) {
      var dist = pointToSegmentDistance(pt, link.data('fromPt'), link.data('toPt'));
      var diff = link === linkState.link ? 10 : 0;

      if (minPath.dist > dist - diff && dist < linkState.avgLen) {
        minPath.dist = dist - diff;
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
    var lastStart = linkState.atStart;
    var linkText, handleChanged;

    if (link) {
      linkState.atStart = getDistance(pt, link.data('fromPt')) < getDistance(pt, link.data('toPt'));
      linkState.handlePt = link.data(linkState.atStart ? 'fromPt' : 'toPt');
      linkText = (linkState.atStart ? '*' : '') + link.data('cid1').replace(linkState.colId, '')
          + '->' + (linkState.atStart ? '' : '*') + link.data('cid2').replace(linkState.colId, '');
    }
    handleChanged = linkState.link !== link || lastStart !== linkState.atStart;
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
          if (p.data('colId') === linkState.colId && p !== link) {
            p.setAttr({'stroke-width': linkState.curColWidth / data.ratioInitial});
          }
        });
        if (linkState.alongDot) {
          linkState.alongDot.remove();
        }
        var alongPath = colPaths[linkState.colId];
        if (alongPath) {
          linkState.alongLen = alongPath.getTotalLength();
          linkState.alongDot = data.paper.circle(0, 0, 2).attr({stroke: '#f00', fill: '#fff'});

          data.paper.customAttributes.along = function (v) {
            var point = alongPath.getPointAtLength(v * linkState.alongLen);
            return point && {
              transform: "t" + [point.x, point.y] + "r" + point.alpha
            };
          };
          linkState.alongDot.attr({along: 0});

          function run() {
            if (links[linkState.colId]) {
              var ms = 150 * links[linkState.colId].length;
              linkState.alongDot.animate({along: 1}, ms, function () {
                linkState.alongDot.attr({along: 0});
                setTimeout(run);
              });
            }
          }
          setTimeout(run);
        }
      }
      if (link) {
        link.setAttr({'stroke-width': linkState.curLinkWidth / data.ratioInitial, 'stroke-opacity': 0.8});
      }
    }
    createHandle('handle', linkState.handlePt, link && link.data(linkState.atStart ? 'cid1' : 'cid2'), handleChanged);

    $('#info > .col-info').text(linkState.colId ? '栏: ' + linkState.colId : '');
    $('#info > .char-info').text(linkText ? '字: ' + linkText : '');
  }

  function mouseDown(pt) {
    if (linkState.handle) {
      linkState.handle.attr({'stroke-opacity': 0.2});
      linkState.link.attr({'stroke-opacity': 0.2});
    }
    mouseDrag(pt);
  }

  function mouseDrag(pt) {
    if (linkState.link) {
      linkState.dragTarget = $.cut.findBoxByPoint(pt);
      if (linkState.dragTarget) {
        pt = getCenter(linkState.dragTarget);
      }
      $('#info > .target-char').text(linkState.dragTarget ?
          linkState.dragTarget.data('cid').replace(linkState.colId, '') : '');

      createHandle('draggingHandle', pt, linkState.dragTarget && linkState.dragTarget.data('cid'));
      if (linkState.dynLink) {
        linkState.dynLink.remove();
      }
      if (linkState.atStart) {
        linkState.dynLink = buildArrayLink(pt, linkState.link.data('toPt'),
          10, null, null, null, '#f00');
      } else {
        linkState.dynLink = buildArrayLink(linkState.link.data('fromPt'), pt,
            10, null, null, null, '#f00');
      }
      linkState.dynLink.setAttr({'stroke-width': linkState.curLinkWidth / data.ratioInitial, 'stroke-opacity': 0.7});
    }
  }

  function mouseUp() {
    if (linkState.draggingHandle) {
      var cidNew = linkState.draggingHandle.data('cid');
      var cidOld = linkState.handle.data('cid');

      linkState.draggingHandle.remove();
      delete linkState.draggingHandle;
      linkState.dynLink.remove();
      delete linkState.dynLink;

      if (cidNew && cidOld && cidNew !== cidOld) {
        var charOld = $.cut.findCharById(cidOld);
        var charNew = $.cut.findCharById(cidNew);
        var t;
        ['block_no', 'line_no', 'char_no', 'no', 'char_id'].forEach(function (f) {
          t = charOld[f];
          charOld[f] = charNew[f];
          charNew[f] = t;
        });
        charOld.shape.data('cid', charOld.char_id);
        charNew.shape.data('cid', charNew.char_id);
        setTimeout(function () {
          $.cut.addCharOrderLinks();
        }, 500);
      }
      if (linkState.dragTarget) {
        $('#info > .target-char').text('');
      }
    }
    if (linkState.handle) {
      linkState.handle.attr({'stroke-opacity': 1})
    }
  }

  function createHandle(name, pt, cid, switched) {
    if (linkState[name] && !pt) {
      linkState[name].remove();
      delete linkState[name];
    }
    if (linkState[name] && pt) {
      linkState[name].animate({cx: pt.x, cy: pt.y, r: 5}, 300, 'elastic');
    }
    else if (linkState.link && pt) {
      linkState[name] = data.paper.circle(pt.x, pt.y, switched ? 8 : 5)
          .attr({fill: 'rgba(0,255,0,.4)'});
      if (switched) {
        linkState[name].animate({r: 5}, 1000, 'elastic');
      }
    }
    if (cid) {
      linkState[name].data('cid', cid);
    }
  }

  $.extend($.cut, {
    removeCharOrderLinks: function () {
      delete linkState.colId;

      paths.forEach(function (link) {
        link.remove();
      });
      links = {};
      paths = [];

      texts.forEach(function (text) {
        text.remove();
      });
      texts = [];

      Object.keys(colPaths).forEach(function (id) {
        colPaths[id].remove();
      });
      colPaths = {};

      if (linkState.handle) {
        linkState.handle.remove();
        delete linkState.handle;
      }
      if (linkState.draggingHandle) {
        linkState.draggingHandle.remove();
        delete linkState.draggingHandle;
      }
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
          if (linkState.textVisible) {
            var cen = getCenter(box);
            texts.push(data.paper.text(cen.x, cen.y, nums.slice(1, 3).join('c'))
                .attr({'font-size': '13px'}));
          }
        }
      });

      Object.keys(links).forEach(function (colId, colIndex) {
        var column = links[colId] = links[colId].sort(function (a, b) {
          return a[0] - b[0];
        }).map(function (a) {
          return {char: a[1], link: null};
        });

        linkState.avgLen = 0;
        var points = [getCenter(column[0].char)];
        column.forEach(function (c, i) {
          if (i > 0) {
            var h = Math.min(getHeight(column[i - 1].char), getHeight(c.char));
            var fromPt = getCenter(column[i - 1].char);
            var toPt = getCenter(c.char);

            linkState.avgLen += getDistance(fromPt, toPt);
            c.link = buildArrayLink(fromPt, toPt, h / 4, column[i - 1].char, c.char, colId, colIndex % 2 ? '#00f' : '#07f');
            paths.push(c.link);
            points.push(toPt);
          }
        });
        if (linkState.avgLen) {
          linkState.avgLen /= column.length - 1;
        }
        colPaths[colId] = data.paper.path(points.map(function (pt, i) {
          return (i > 0 ? 'L' : 'M') + round(pt.x) + ',' + round(pt.y);
        }).join(' ')).attr({stroke: 'none'});
      });
    }
  });

  state.onZoomed = function () {
    if (paths.length) {
      $.cut.addCharOrderLinks();
    }
  };

  $('#switch-char-no').click(function () {
    linkState.textVisible = !linkState.textVisible;
    $.cut.addCharOrderLinks();
  });
}());
