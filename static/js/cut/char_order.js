/*
 * char_order.js
 * 字序调整的显示、交互和计算
 * Date: 2019-06-26
 * global $
 */
(function () {
  'use strict';

  // 通用计算函数
  //

  // 计算两点的距离
  var getDistance = $.cut.getDistance;

  // 四舍五入，保留2位小数
  function round(num) {
    return Math.round(num * 100) / 100;
  }

  // 计算一点到线段的最短距离
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

  // 销毁所有图形，obj 可为图形对象的容器对象或数组，或有remove方法的对象
  function removeShapes(obj) {
    if (!obj) {
    } else if (obj instanceof Array) {
      while (obj.length) {
        removeShapes(obj.pop());
      }
    } else if (obj.remove) {
      obj.remove();
    } else {
      Object.keys(obj).forEach(function (k) {
        if (obj[k] instanceof Array) {
          removeShapes(obj[k]);
        } else {
          if (obj[k] && obj[k].remove) {
            obj[k].remove();
            obj[k] = null;
          }
        }
      });
    }
  }

  function getId(obj) {
    obj = obj && obj.obj || obj;
    return obj ? obj.getId() : '';
  }

  var LET_RADIUS = 3;
  var colors = {
    link: ['#00f', '#08f', '#f00'], // 两个交替列的线色、改动色
    sel: '#00f'   // 选中对象的颜色
  };
  var data = $.cut.data;
  var state = $.cut.state;

  // 字框图形类
  function CharNode(char) {
    this.shapes = {};
    char = this.char = char instanceof CharNode ? char.char : char;
    console.assert(char && char.shape && char.char_id);
    console.assert(char.shape.getBBox());
  }

  CharNode.prototype = {
    // 得到编号
    getId: function () {
      return this.char.char_id + (this.char.id ? '#' + this.char.id : '');
    },

    // 是否为合法的字框编号
    isValidId: function () {
      return /^b[1-9]c\d{1,2}c\d{1,2}$/.test(this.char.char_id);
    },

    // 得到字框矩形
    getBox: function () {
      return this.char.shape.getBBox();
    },

    // 得到字框中心坐标
    getCenter: function () {
      return $.cut.getHandle(this.char.shape, 8);
    },

    // 得到左边的入点和右边的出点坐标
    getLets: function () {
      var box = this.getBox(), y = (box.y + box.y2) / 2;
      return [{x: box.x + box.width * 0.3, y: y}, {x: box.x + box.width * 0.7, y: y}];
    },

    // 创建亮显矩形
    createBox: function (color) {
      var box = this.getBox();
      return data.paper.rect(box.x, box.y, box.width, box.height)
          .initZoom()
          .setAttr({
            stroke: color,
            fill: color,
            'stroke-opacity': 0.5,
            'fill-opacity': 0.15,
            'stroke-width': 1.5 / data.ratioInitial
          });
    },

    // 创建亮显出入点
    createLet: function (inlet, zoomed) {
      var pt = this.getLets()[inlet ? 0 : 1];
      var color = inlet ? '#f00' : '#07f';
      var dot = data.paper.circle(pt.x, pt.y, 1)
          .initZoom()
          .setAttr({
            stroke: color,
            fill: color,
            'stroke-opacity': zoomed ? 0.7 : 0.5,
            'fill-opacity': 0,
            'stroke-width': 1.5 / data.ratioInitial
          })
          .data('node', this);
      dot.animate({
        r: Math.max(LET_RADIUS * 1.5 * data.ratio, 6),
        'fill-opacity': zoomed ? 0.8 : 0.1
      }, 500, 'elastic');
      return dot;
    },

    // 检测能否点中入点
    hitTestInlet: function (pt, tol, mask) {
      if (mask && mask.only && !mask.only.inlet || mask && mask.not && mask.not.inlet) {
        return;
      }
      var dist = getDistance(pt, this.getLets()[0]);
      if (dist < tol) {
        return {dist: dist, obj: this, type: 'inlet'};
      }
    },

    // 检测能否点中出点
    hitTestOutlet: function (pt, tol, mask) {
      if (mask && mask.only && !mask.only.outlet || mask && mask.not && mask.not.outlet) {
        return;
      }
      var dist = getDistance(pt, this.getLets()[1]);
      if (dist < tol) {
        return {dist: dist, obj: this, type: 'outlet'};
      }
    }
  };

  // 字框连线类(c1出点->c2入点)
  function Link(c1, c2) {
    if (c1 instanceof Link) {
      this.source = c1;   // source 为原始连接对象
      c2 = c1.c2;
      c1 = c1.c1;
    }
    console.assert(c1 instanceof CharNode && c2 instanceof CharNode);
    this.c1 = c1;
    this.c2 = c2;
    this.shapes = {};
  }

  Link.prototype = {
    // 得到编号
    getId: function () {
      if (this.c1 && this.c2) {
        var a = this.c1.getId().split('c'), b = this.c2.getId().split('c');
        return this.c1.getId() + '-' + (a.length === 3 && a[0] === b[0] && a[1] === b[1] ? 'c' + b[2] : this.c2.getId());
      }
    },

    // 销毁所有图形
    remove: function () {
      removeShapes(this.shapes);
    },

    // 得到起点坐标
    getStartPos: function () {
      return this.c1.getLets()[1];
    },

    // 得到终点坐标
    getEndPos: function () {
      return this.c2.getLets()[0];
    },

    // 是独占一列的回环连接
    isSelfLink: function () {
      return this.c1 === this.c2;
    },

    // 创建亮显连线
    createLine: function (color, zoomed) {
      return this.createLineWith(this.getStartPos(), this.getEndPos(), color, zoomed);
    },

    // 指定端点坐标创建亮显连线
    createLineWith: function (a, b, color, zoomed) {
      var remove = zoomed === 'remove';
      var up = a.y > b.y + (this.c2 || this.c1).getBox().height * 0.3;
      var line = data.paper.path('M' + a.x + ',' + a.y + 'L' + b.x + ',' + b.y)
          .initZoom()
          .setAttr({
            stroke: color,
            'stroke-opacity': zoomed ? 0.4 : 0.6,
            'stroke-width': 3 / data.ratioInitial,
            'stroke-linecap': up && !zoomed ? 'butt' : 'round'
          })
          .data('id', this.getId())
          .data('link', this);

      if (remove) {
        line.setAttr({
          'stroke-dasharray': '.',
          'stroke-width': 1 / data.ratioInitial
        });
      } else if (up && !zoomed) {
        line.setAttr({
          'stroke-dasharray': '.',
          'stroke-width': 2 / data.ratioInitial
        });
      }
      if (zoomed && !remove) {
        line.animate({'stroke-width': 6 * data.ratio}, 500, 'elastic');
      }
      return line;
    },

    // 检测能否点中连线
    hitTestLink: function (pt, tol, mask) {
      if (mask && mask.only && !mask.only.link || mask && mask.not && mask.not.link) {
        return;
      }
      var a = this.getStartPos(), b = this.getEndPos();
      var dist = pointToSegmentDistance(pt, a, b);
      var awayFromLet = LET_RADIUS * 2 + 5;
      if (dist < tol) {
        if (getDistance(pt, a) > awayFromLet && getDistance(pt, b) > awayFromLet) {
          return {dist: dist, obj: this, type: 'link'};
        }
      }
    }
  };

  // 字框集类
  function CharNodes(src) {
    this.shapes = {};
    this.linksOfCol = [];   // [[Link...], links_of_another_column...]
    this.hover = {};        // 鼠标掠过时的动态图形
    this.drag = {};         // 拖拽过程中的动态图形
    this.errNodes = [];     // 有问题的字框的高亮矩形
    this.label = [];        // 字框编号文字
    this.links = [];        // linksOfCol中的连线，及新增连线
    this.state = {tol: 1};
    this.changed = false;

    // 创建字框节点
    console.assert(src instanceof Array);
    this.nodes = src.map(function (char) {
      if (char.shape && char.char_id) {
        return new CharNode(char);
      }
    }).filter(function (char) {
      return char;
    });
  }


  CharNodes.prototype = {
    // 销毁所有图形
    remove: function () {
      removeShapes(this.shapes);
      removeShapes(this.links);   // links已经包含了linksOfCol里的连线
      removeShapes(this.hover);
      removeShapes(this.drag);
      removeShapes(this.errNodes);
      removeShapes(this.label);
    },

    // 根据每列的字框序号构建分列图形
    buildColumns: function (chars_col) {
      var self = this;
      self.state.avgLen = 0;
      this.remove();
      this.chars_col = chars_col || this.chars_col || [];
      this.linksOfCol = this.chars_col.map(function (ids, colIndex) {
        return (ids.length === 1 ? ids : ids.slice(1)).map(function (id, i) {
          var c1 = self.findNode(ids[i]), c2 = self.findNode(id);
          if (!c1 || !c2 || !c1.isValidId() || !c2.isValidId()) {
            return;
          }
          var link = new Link(c1, c2);
          link.shapes.line = link.createLine(colors.link[colIndex % 2]);
          self.links.push(link);
          self.state.avgLen += getDistance(link.getStartPos(), link.getEndPos());
          return link;
        }).filter(function (link) {
          return link;
        });
      });
      self.state.avgLen /= Math.max(1, self.links.length);
      self.checkLinks();
      self.updateLabel();
    },

    // 更新字框编号文字
    updateLabel: function () {
      removeShapes(this.label);
      var self = this;
      if (this.state.labelVisible) {
        this.nodes.forEach(function (node) {
          if (node.isValidId()) {
            var cen = node.getCenter(), nums = node.getId().replace(/#.+$/, '').split('c');

            self.label.push(data.paper.text(cen.x, cen.y, nums[2])
                .attr({'font-size': (14 * $.cut.data.ratio) + 'px'}));
          }
        });
      }
    },

    // 根据字框编号、字框图形或坐标查找 CharNode 对象
    findNode: function (c) {
      c = typeof c === 'number' ? $.cut.findCharById(c) : (c.x || c.y) ? $.cut.findBoxByPoint(c) : c;
      return this.nodes.filter(function (node) {
        return node.char === c || node.char.shape === c;
      })[0];
    },

    // 查找一个字框的入线，即连线的终点为指定的字框
    findInLinks: function (node) {
      var id = getId(node);
      return this.links.filter(function (link) {
        return getId(link.c2) === id;
      });
    },

    // 查找一个字框的出线，即连线的起点为指定的字框
    findOutLinks: function (node) {
      var id = getId(node);
      return this.links.filter(function (link) {
        return getId(link.c1) === id;
      });
    },

    // 查找两个字框之间的连线
    findLinkBetween: function (c1, c2) {
      return this.links.filter(function (link) {
        return link.c1 === c1 && link.c2 === c2 || link.c2 === c1 && link.c1 === c2;
      })[0];
    },

    // 检测能否点中
    hitTest: function (pt, node, mask) {
      var found = [];
      var tol = this.state.avgLen || 1;

      // 如果指定了字框，则在其中找入点和出点，否则在所有字框中找出入点
      if (node) {
        found.push(node.hitTestInlet(pt, tol, mask));
        found.push(node.hitTestOutlet(pt, tol, mask));
      } else {
        this.nodes.forEach(function (d) {
          found.push(d.hitTestInlet(pt, tol, mask));
          found.push(d.hitTestOutlet(pt, tol, mask));
        });
      }

      // 找最近的连线
      this.links.forEach(function (link) {
        var r = link.hitTestLink(pt, tol, mask);
        if (r) {
          tol = Math.min(tol, r.dist + 2);
          found.push(r);
        }
      });

      // 取距离最近的
      found.sort(function (a, b) {
        return (a && a.dist || 1e5) - (b && b.dist || 1e5);
      });
      return found[0];
    },

    // 鼠标掠过时捕捉和高亮显示. 如果字框没有连线，则捕捉出入点，否则捕捉连线
    mouseHover: function (pt) {
      var hit = this.hitTest(pt, null);
      var links, changed;

      // 如果字框没有连线，则捕捉出入点，否则捕捉连线
      if (hit && hit.type !== 'link') {
        links = hit.type === 'inlet' ? this.findInLinks(hit.obj) : this.findOutLinks(hit.obj);
        if (links.length === 1) {
          hit.obj = links[0];
          hit.type = 'link';
        } else if (links.length > 1) {
          hit = this.hitTest(pt, null, {only: {link: true}});
        }
      }

      // 捕捉并高亮显示，如果为出入点则该点没有连线
      if (!hit || getId(hit) !== getId(this.state.hit) || hit.type !== this.state.hit.type) {
        removeShapes(this.hover);
        this.state.hit = hit;
        changed = true;
        if (hit && hit.type !== 'link') {
          this.hover.inlet = hit.type === 'inlet' && hit.obj.createLet(true, true);
          this.hover.outlet = hit.type === 'outlet' && hit.obj.createLet(false, true);
        }
      }

      if (hit && hit.type === 'link') {
        this._updateCurrentLink(hit.obj, pt);
      } else {
        this.state.inletHit = hit && hit.type !== 'inlet';
        this.state.outletHit = hit && hit.type !== 'outlet';
      }

      if (changed) {
        this.linkSwitched();
      } else {
        this._updateCharInfo(this.state.hit);
      }
    },

    _updateCharInfo: function (link) {
      $('#info > .char-info').text('字框连线: ' + (getId(link) || (this.state.dragLink ? '将断开' : '未选中')) +
          (this.state.inletHit ? '，可改终点' : (this.state.outletHit ? this.hover.line ? '，可改起点' : '，起点' : '')));
    },

    linkSwitched: function (link, ballTimes) {
      var self = this;
      link = getId(this.state.dragLink) && this.state.dragLink || this.state.hit || link;
      var run = function () {
        var alongPath = self.drag.line || self.hover.line;
        if (self.hover.ball && alongPath && --self.state.ballTimes >= 0) {
          var ms = Math.max(alongPath.getTotalLength() / self.state.avgLen - 1, 0) * 100 + 200;
          self.hover.ball.attr({alongLink: 0});
          self.hover.ball.animate({alongLink: 1}, ms, function () {
            setTimeout(run, 100);
          });
        }
      };

      this._updateCharInfo(link);
      removeShapes(this.hover.ball);
      if (link) {
        data.paper.customAttributes.alongLink = function (v) {
          var alongPath = self.drag.line || self.hover.line;
          var point = alongPath && alongPath.getPointAtLength(v * alongPath.getTotalLength());
          return point && {transform: "t" + [point.x, point.y] + "r" + point.alpha};
        };
        self.hover.ball = data.paper.circle(0, 0, 2).attr({stroke: '#f00', fill: '#fff', 'z-order': 1000});
        self.state.ballTimes = ballTimes || 5;
        setTimeout(run, 100);
      }
    },

    // 拖拽出入点到字框或空白处
    mouseDrag: function (pt) {
      if (!this.state.dragging && (this.state.inletHit || this.state.outletHit && this.hover.line)) {
        this.state.dragging = getDistance(state.downOrigin, pt) > this.state.avgLen / 3;
        if (!this.state.dragging) {
          return;
        }
        this.state.dragLink = this.hover.line ? new Link(this.state.hit.obj)
            : new Link(this.state.hit.obj, this.state.hit.obj);
        if (this.hover.line) {
          this.hover.line.attr({'stroke-opacity': 0.05});
          var srcLink = this.findLinkBetween(this.state.dragLink.c1, this.state.dragLink.c2);
          srcLink.shapes.line.attr({'opacity': 0.05});
        }
        if (this.hover.inlet && this.state.inletHit) {
          this.hover.inlet.attr({'fill-opacity': 0});
        }
        if (this.hover.outlet && this.state.outletHit) {
          this.hover.outlet.attr({'fill-opacity': 0});
        }
        this.linkSwitched(null, 200);
      }
      if (this.state.dragging) {
        var hit = this.hitTest(pt, this.findNode(pt), {
          only: {inlet: this.state.inletHit, outlet: this.state.outletHit}
        });
        var node = hit && hit.obj;

        if (!node || getId(node) !== getId(this.state.targetNode)) {
          this.state.targetNode = node;
          if (this.state.inletHit) {
            this.state.dragLink.c2 = node;
          } else {
            this.state.dragLink.c1 = node;
          }
          removeShapes(this.drag);
          if (hit) {
            this.drag.box = node && node.createBox(colors.sel);
            this.drag.dot = hit && hit.obj.createLet(hit.type === 'inlet');
            this.drag.line = this.state.dragLink.createLine(colors.sel);
          } else {
            this.drag.line = this.state.dragLink.createLineWith(
                this.state.outletHit ? pt : this.state.dragLink.getStartPos(),
                this.state.inletHit ? pt : this.state.dragLink.getEndPos(),
                colors.sel, 'remove');
          }
          if (this.hover.ball) {
            this.hover.ball.toFront();
          }
        }
      }
    },

    mouseUp: function (pt, e) {
      var link = this.state.dragLink, srcLink = link && link.source;
      var changed;
      var enableSelfLink = e.shiftKey;

      // 恢复原连接的透明度
      if (srcLink && srcLink.shapes.line) {
        srcLink.shapes.line.attr({'opacity': 1});
      }
      if (link && (link.c1 !== link.c2 || enableSelfLink) && (!srcLink || srcLink.shapes.line)) {
        // 改变原连接的端点
        if (srcLink && (link.c1 !== srcLink.c1 || link.c2 !== srcLink.c2)) {
          if (link.c1 && link.c2) {
            changed = this.moveLink(srcLink.c1, srcLink.c2, link.c1, link.c2);
          } else {
            changed = this.delLink(srcLink.c1, srcLink.c2);
          }
        }
        // 新加连接
        else if (!srcLink) {
          changed = this.addLink(link.c1, link.c2);
        }
      }
      this.state.dragging = false;
      removeShapes(this.drag);
      delete this.state.targetNode;
      delete this.state.dragLink;

      if (changed) {
        this.changed = true;
        this.checkLinks();
        this._updateCurrentLink(changed, pt);
        this.linkSwitched(changed instanceof Link && changed);
      }
    },

    // 更新当前连接
    _updateCurrentLink: function (link, pt) {
      if (!pt || !this.hover.line || !link || this.hover.line.data('id') !== link.getId()) {
        removeShapes(this.hover.line);
        this.hover.line = link instanceof Link && link.createLine(colors.sel, true);
      }

      var inletHit = pt && getDistance(pt, link.getEndPos()) < getDistance(pt, link.getStartPos());
      var outletHit = pt && getDistance(pt, link.getEndPos()) > getDistance(pt, link.getStartPos());

      if (!this.hover.inlet || inletHit !== this.state.inletHit || !pt) {
        this.state.inletHit = inletHit;
        removeShapes(this.hover.inlet);
        this.hover.inlet = link && link.c2.createLet(true, inletHit);
      }
      if (!this.hover.outlet || outletHit !== this.state.outletHit || !pt) {
        this.state.outletHit = outletHit;
        removeShapes(this.hover.outlet);
        this.hover.outlet = link && link.c1.createLet(false, outletHit);
      }

      if (this.hover.ball) {
        this.hover.ball.toFront();
      }
    },

    // 断开连接
    delLink: function (c1, c2) {
      var link = this.findLinkBetween(c1, c2);
      if (link) {
        this.changed = true;
        link.remove();
        this.links.splice(this.links.indexOf(link), 1);
        return true;
      }
    },

    // 新加连接
    addLink: function (c1, c2) {
      var link = this.findLinkBetween(c1, c2);
      if (!link && c1 && c2 && c1 !== c2) {
        this.changed = true;
        link = new Link(c1, c2);
        link.shapes.line = link.createLine(colors.link[2]);
        this.links.push(link);
        return link;
      }
    },

    // 移动连接
    moveLink: function (c1Old, c2Old, c1New, c2New) {
      var link = this.findLinkBetween(c1Old, c2Old);
      if (link && c1New && c2New) {
        this.changed = true;
        link.remove();
        link.c1 = c1New;
        link.c2 = c2New;
        link.shapes.line = link.createLine(colors.link[2]);
        return link;
      }
    },

    // 当前连接反向
    reverseLink: function () {
      var link = (this.state.hit || {}).obj;
      if (link instanceof Link && !this.drag.line) {
        this.changed = true;
        this.moveLink(link.c1, link.c2, link.c2, link.c1);
        this._updateCurrentLink(link);
        this.linkSwitched(link);
      }
    },

    checkLinks: function (routes, heads) {
      if (!this.chars_col || !this.chars_col.length) {
        return;
      }

      var self = this;
      var errors = [];
      var tails = [];
      var used = [];

      heads = heads === undefined ? [] : heads;

      // 每个字框的出入点至少有一个有连接，一个点最多一个连接
      this.nodes.forEach(function (node) {
        var linksIn = self.findInLinks(node);
        var linksOut = self.findOutLinks(node);

        if (!linksIn.length && !linksOut.length || linksIn.length > 1 || linksOut.length > 1) {
          errors.push(node);
        } else if (!linksIn.length && linksOut.length === 1) {
          heads.push(node);
        } else if (!linksOut.length && linksIn.length === 1) {
          tails.push(node.getId());
        } else if (linksOut.length === 1 && linksOut[0].isSelfLink()) {
          heads.push(node);
          tails.push(node.getId());
        }
      });

      // 从开始字框到结束字框应有且仅有一条通路
      function pass(node, route) {
        if (used.indexOf(node) >= 0) {
          errors.push(node);
          return;
        }
        used.push(node);
        route.push(node.char);

        var links = self.findOutLinks(node);
        if (links.length === 1 && errors.indexOf(links[0]) < 0 && links[0].c2 !== node) {
          pass(links[0].c2, route);
        }
      }

      heads.forEach(function (node) {
        var route = [];
        pass(node, route);
        if (routes) {
          routes.push(route);
        }
      });

      // 高亮有问题的字框
      removeShapes(this.errNodes);
      errors.forEach(function (node) {
        var r = node.createBox('#ff0');
        r.animate({'fill-opacity': 0.3}, 1000, 'elastic');
        self.errNodes.push(r);
      });

      return !errors.length && used.length === this.nodes.length;
    }
  };

  var cs;

  function mouseHover(pt) {
    cs.mouseHover(pt);
  }

  function mouseDown(pt) {
  }

  function mouseDrag(pt) {
    cs.mouseDrag(pt);
  }

  function mouseUp(pt, e) {
    cs.mouseUp(pt, e);
  }

  $.extend($.cut, {
    removeCharOrderLinks: function () {
      if (cs) {
        cs.remove();
      }
    },

    addCharOrderLinks: function (chars_col) {
      if (!cs) {
        cs = new CharNodes(data.chars);
        cs.buildColumns(chars_col);
      }
      state.mouseHover = mouseHover;
      state.mouseDown = mouseDown;
      state.mouseDrag = mouseDrag;
      state.mouseUp = mouseUp;
      return cs;
    },

    bindCharOrderKeys: function () {
      var self = this;
      var on = function (key, func) {
        $.mapKey(key, func, {direction: 'down'});
      };

      // r: 当前连接反向
      on('r', function () {
        cs.reverseLink();
      });

      // DEL: 断开当前连接
      state.beforeRemove = function () {
        var link = (cs.state.hit || {}).obj;
        if (link instanceof Link && cs.delLink(link.c1, link.c2)) {
          cs._updateCurrentLink();
          cs.linkSwitched();
        }
        return true;
      };
    },

    // 切换显隐列框
    toggleColumns: function (columns) {
      if (cs.state.columns) {
        cs.state.columns.forEach(function (r) {
          r.animate({opacity: 0}, 200, '>', function () {
            this.remove();
          });
        });
        delete cs.state.columns;
      } else {
        var s = data.ratio * data.ratioInitial;
        cs.state.columns = columns.map(function (box, i) {
          var color = i % 2 ? '#f00' : '#f80';
          var r = data.paper.rect(box.x * s, box.y * s, box.w * s, box.h * s)
              .attr({stroke: color, fill: color, 'stroke-opacity': 0.4, 'fill-opacity': 0});
          r.animate({'fill-opacity': 0.1}, 500, '<');
          return r;
        });
      }
    },

    // 检查错漏
    showErrorBoxes: function (prompt) {
      var r = cs.checkLinks();
      if (prompt) {
        if (r) {
          showSuccess('字框连接正常', '没有待修正的字框连线。');
        } else {
          showError('字框连线有误', '请修正黄色字框的连线。');
        }
      }
    },

    isLinkChanged: function () {
      return cs && cs.changed;
    },

    // 获取字序的Links数据
    getLinkData: function (blocks, columns) {
      var routes = [], heads = [], has_error = false;

      if (!cs.checkLinks(routes, heads)) {
        showError('字框连线有误，请修正黄色字框的连线。');
        has_error = true;
      }
      var chars_col = routes.map(function (route) {
        return route.map(function (char) {
          return char.id;
        });
      });
      return {
        blocks: blocks, columns: columns, chars_col: chars_col,
        chars: $.cut.exportBoxes(), has_error: has_error
      };
    }
  });

  // 放缩后重新生成图形
  state.onZoomed = function () {
    cs && cs.buildColumns();
  };

  // Undo/Redo后重新生成图形
  $.cut.onBoxChanged(function (info, box, reason) {
    if (cs && reason === 'undo') {
      cs.buildColumns();
    }
  });

  // 显隐字框编号
  $('#toggle-char-no').click(function () {
    cs.state.labelVisible = !cs.state.labelVisible;
    cs.updateLabel();
  });


}());
