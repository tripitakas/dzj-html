(function() {
  'use strict';

  var data = $.cut.data;
  var fillColor = '#00f';
  var allHide = false;

  function isOverlap(r1, r2, tol) {
    return r1.x + r1.width > r2.x + tol &&
      r2.x + r2.width > r1.x + tol &&
      r1.y + r1.height > r2.y + tol &&
      r2.y + r2.height > r1.y + tol;
  }

  $.extend($.cut, {

    clearHighlight: function() {
      (data.highlight || []).forEach(function(box) {
        box.remove();
      });
      delete data.highlight;
    },

    highlightBoxes: function(kind, test, retain) {
      var chars = data.chars.filter(function(c) {
        return c.shape;
      });
      var sizes, mean, boxes, highlight;

      if (kind === 'large' || kind === 'small') {
        sizes = chars.map(function(c) {
          var r = c.shape.getBBox();
          return r && c.ch !== '一' && r.width * r.height;
        }).filter(function(c) {
          return c;
        });
        sizes.sort();
        mean = sizes[parseInt(sizes.length / 2)];
      }
      if (kind === 'all' && !retain) {
        allHide = !allHide;
      }

      if (!test) {
        this.clearHighlight();
      }
      highlight = chars.map(function(c) {
        var r = c.shape && c.shape.getBBox();
        if (r) {
          var degree = 0;

          if (kind === 'large') {
            degree = r.width * r.height / mean - 1;
            if (degree < 0.5) {
              return;
            }
          }
          else if (kind === 'small') {
            degree = mean / (r.width * r.height) - 1;
            if (degree < 0.5 || c.ch === '一') {
              return;
            }
          }
          else if (kind === 'narrow') {
            degree = r.height / r.width - 1;
            if (degree < 0.5) {
              return;
            }
          }
          else if (kind === 'flat') {
            degree = r.width / r.height - 1;
            if (degree < 0.5 || c.ch === '一') {
              return;
            }
          }
          else if (kind === 'overlap') {
            boxes = chars.filter(function(c2) {
              return c2 !== c && isOverlap(r, c2.shape.getBBox(), 2);
            });
            if (boxes.length < 1) {
              return;
            }
            degree = 0.5;
            if (boxes.filter(function(c2) {
                return isOverlap(r, c2.shape.getBBox(), 5);
              }).length) {
              degree = 0.7;
              if (boxes.filter(function(c2) {
                  return isOverlap(r, c2.shape.getBBox(), 10);
                }).length) {
                degree = 0.9;
                if (boxes.filter(function(c2) {
                    return isOverlap(r, c2.shape.getBBox(), 15);
                  }).length) {
                  degree = 1.1;
                }
              }
            }
          }
          return test ? [c.char_id, degree] : data.paper.rect(r.x, r.y, r.width, r.height)
            .initZoom().setAttr({
              stroke: 'transparent',
              fill: kind === 'all' && allHide ? '#fff' : $.cut.rgb_a(fillColor,
                degree >= 1.05 ? 0.8 :
                degree >= 0.90 ? 0.65 :
                degree >= 0.75 ? 0.5 :
                degree >= 0.60 ? 0.35 : 0.25)
            })
            .data('highlight', c.char_id);
        }
      }).filter(function(box) { return box; });

      if (!test) {
        highlight.sort(function(a, b) {
          a = a.getBBox();
          b = b.getBBox();
          return Math.abs(a.x - b.x) < Math.min(a.width, b.width) / 2 ? a.y - b.y : a.x - b.x;
        });
        data.highlight = highlight;
      }
      return highlight;
    }
  });
}());
