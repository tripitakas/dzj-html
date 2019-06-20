/*
 * proofread.js
 *
 * Date: 2018-9-19
 */

/*-----------切分字框相关代码----------------*/
var showBlockBox = false;                 // 是否显示栏框切分坐标
var showColumnBox = false;                // 是否显示列框切分坐标
var showOrder = false;                    // 是否显示字框对应序号
var showText = false;                     // 是否显示字框对应文字
var lineNos = [];
var currentSpan = [];


function findBestBoxes(offset, block_no, line_no, cmp) {
    var minNo = 10;
    var ret;
    $.cut.findCharsByLine(block_no, line_no, function (ch, box) {
        if (cmp(ch)) {
            if (minNo > Math.abs(offset + 1 - box.char_no)) {
                minNo = Math.abs(offset + 1 - box.char_no);
                ret = box;
            }
        }
    });
}

function unicodeValuesToText(values) {
    return values.map(function (c) {
        return /^[A-Za-z0-9?*]$/.test(c) ? c : c.length > 2 ? decodeURIComponent(c) : ' ';
    }).join('');
}

function getLineText($line) {
    var chars = [];
    $line.find('span').each(function (i, el) {
        if ($(el).hasClass('variant')) {
            chars.push($(el).text());
        } else {
            var text = $(el).text().replace(/\s/g, '');
            chars = chars.concat(text.split(''));
        }
    });
    return chars;
}

// 获取当前光标位置
function getCursorPosition(element) {
    var caretOffset = 0;
    var doc = element.ownerDocument || element.document;
    var win = doc.defaultView || doc.parentWindow;
    var sel, range, preCaretRange;

    if (typeof win.getSelection !== 'undefined') {    // 谷歌、火狐
        sel = win.getSelection();
        if (sel.rangeCount > 0) {                       // 选中的区域
            range = win.getSelection().getRangeAt(0);
            caretOffset = range.startOffset;
            // preCaretRange = range.cloneRange();         // 克隆一个选中区域
            // preCaretRange.selectNodeContents(element);  // 设置选中区域的节点内容为当前节点
            // preCaretRange.setEnd(range.endContainer, range.endOffset);  // 重置选中区域的结束位置
            // caretOffset = preCaretRange.toString().length;
        }
    } else if ((sel = doc.selection) && sel.type !== 'Control') {    // IE
        range = sel.createRange();
        preCaretRange = doc.body.createTextRange();
        preCaretRange.moveToElementText(element);
        preCaretRange.setEndPoint('EndToEnd', range);
        caretOffset = preCaretRange.text.length;
    }
    return caretOffset;
}

// 高亮一行中字组元素对应的字框
function highlightBox($span, first) {
    if (!$span) {
        $span = currentSpan[0];
        first = currentSpan[1];
        if (!$span) {
            return;
        }
    }
    var $line = $span.parent(), $block = $line.parent();
    var block_no = parseInt($block.attr('id').replace(/^.+-/, ''));
    var line_no = parseInt(($line.attr('id') || '').replace(/^.+-/, ''));
    var offset0 = parseInt($span.attr('offset'));
    var offsetInSpan = first ? 0 : getCursorPosition($span[0]);
    var offsetInLine = offsetInSpan + offset0;
    var ocrCursor = ($span.attr('ocr') || '')[offsetInSpan];
    var cmpCursor = ($span.attr('cmp') || '')[offsetInSpan];
    var text = $span.text().replace(/\s/g, '');
    var i, chTmp, all;

    // 根据文字的栏列号匹配到字框的列，然后根据文字精确匹配列中的字框
    var boxes = $.cut.findCharsByLine(block_no, line_no, function (ch) {
        return ch === ocrCursor || ch === cmpCursor;
    });
    // 行内多字能匹配时就取char_no位置最接近的，不亮显整列
    if (boxes.length > 1) {
        boxes[0] = findBestBoxes(offsetInLine, block_no, line_no, function (ch) {
            return ch === ocrCursor || ch === cmpCursor;
        }) || boxes[0];
    }
    // 或者用span任意字精确匹配
    else if (!boxes.length) {
        for (i = 0; i < text.length && !boxes.length; i++) {
            chTmp = text[i];
            boxes = $.cut.findCharsByLine(block_no, line_no, function (ch) {
                return ch === chTmp;
            });
        }
        if (boxes.length > 1) {
            boxes[0] = findBestBoxes(offsetInLine, block_no, line_no, function (ch) {
                return ch === chTmp;
            }) || boxes[0];
        }
    }

    $.cut.removeBandNumber(0, true);
    $.cut.state.focus = false;
    $.fn.mapKey.enabled = false;
    $.cut.data.block_no = block_no;
    $.cut.data.line_no = line_no;
    currentSpan = [$span, first];

    // 按字序号浮动亮显当前行的字框
    text = getLineText($line);
    all = $.cut.findCharsByLine(block_no, line_no);
    $.cut.showFloatingPanel(
        (showOrder || showText) ? all : [],
        function (char, index) {
            return (showOrder ? char.char_no : '') + (!text[index] ? '？' : showText ? text[index] : '');
        },
        highlightBox
    );

    // 显示当前栏框
    if (showBlockBox) {
        $.cut.showBox('blockBox', window.blocks, all.length && all[0].char_id.split('c')[0]);
    }

    // 显示当前列框
    if (showColumnBox) {
        $.cut.showBox('columnBox', window.columns, all.length && all[0].char_id.split('c').slice(0, 2).join('c'));
    }

    $.cut.switchCurrentBox(((boxes.length ? boxes : all)[0] || {}).shape);
}


/*-----------文本区域相关代码----------------*/

// 检查图文匹配，针对字数不匹配的行加下划线
function checkMismatch(report) {
    var mismatch = [];
    var total = '', ocrColumns = [];

    $.cut.data.chars.forEach(function (c) {
        if (c.shape && c.line_no) {
            var t = c.block_no + ',' + c.line_no;
            if (ocrColumns.indexOf(t) < 0) {
                ocrColumns.push(t);
            }
        }
    });
    if (ocrColumns.length !== lineNos.length) {
        total = '文本 ' + lineNos.length + ' 行，图像 ' + ocrColumns.length + ' 行。';
    }
    lineNos.forEach(function (no) {
        var boxes = $.cut.findCharsByLine(no[0], no[1]);
        var $line = $('#block-' + no[0] + ' #line-' + no[1]);
        var text = $line.text().replace(/\s/g, '');
        var len = getLineText($line).length;
        $line.toggleClass('mismatch', boxes.length !== len);
        if (boxes.length !== len) {
            mismatch.push('第 ' + no[1] + ' 行，文本 ' + len + ' 字，图像 ' + boxes.length +
                ' 字。\n' + text + '\n');
        }
    });
    if (report && (total || mismatch.length)) {
        swal('图文不匹配', total + '\n' + mismatch.join('\n'));
    }
}

$(document).ready(function () {
    checkMismatch();
});

$(document).on('click', '.btn-check', function () {
    checkMismatch(true);
});

// 单击异文，弹框提供选择
$(document).on('click', '.not-same', function (e) {
    e.stopPropagation();
    highlightBox($(this), true);

    // 如果是异体字且当前异体字状态是隐藏，则直接返回
    if ($(this).hasClass('variant') && !$(this).hasClass('variant-highlight')) {
        return;
    }

    // 设置当前异文
    $('.not-same').removeClass('current-not-same');
    $(this).addClass('current-not-same');


    var $dlg = $("#pfread-dialog");
    $("#pfread-dialog-cmp").text($(this).attr("cmp"));
    $("#pfread-dialog-base").text($(this).attr("base"));
    $("#pfread-dialog-slct").text($(this).text());
    $dlg.offset({top: $(this).offset().top + 40, left: $(this).offset().left - 4});
    $dlg.show();

    //当弹框超出文字框时，向上弹出
    var r_h = $(".right").height();
    var o_t = $dlg.offset().top;
    var d_h = $dlg.height();
    var shouldUp = false;
    $dlg.removeClass('dialog-common-t');
    $dlg.addClass('dialog-common');
    if (o_t + d_h > r_h) {
        $dlg.offset({top: $(this).offset().top - 180});
        $dlg.removeClass('dialog-common');
        $dlg.addClass('dialog-common-t');
        shouldUp = true;
    }

    // 当弹框右边出界时，向左移动
    var r_w = $dlg.parent()[0].getBoundingClientRect().right;
    var o_l = $dlg.offset().left;
    var d_r = $dlg[0].getBoundingClientRect().right;
    var offset = 0;
    if (d_r > r_w - 20) {
        offset = parseInt(r_w - d_r - 20);
        $dlg.offset({left: o_l + offset});
    }

    var $mark = $dlg.find('.dlg-after');
    var ml = $mark.attr('last-left') || $mark.css('marginLeft');
    if (shouldUp) {
        $mark.attr('last-left', ml);
        $mark.css('marginLeft', parseInt(ml) - offset);
    }

    $mark = $dlg.find('.dlg-before');
    ml = $mark.attr('last-left') || $mark.css('marginLeft');
    if (!shouldUp) {
        $mark.attr('last-left', ml);
        $mark.css('marginLeft', parseInt(ml) - offset);
    }

    // 隐藏当前可编辑同文
    var $curSpan = $('.current-span');
    $curSpan.attr("contentEditable", "false");
    $curSpan.removeClass("current-span");

});

// 单击同文，显示当前span
$(document).on('click', '.same', function () {
    $(".same").removeClass("current-span");
    $(this).addClass("current-span");
    highlightBox($(this));
});

// 双击同文，设置可编辑
$(document).on('dblclick', '.same', function () {
    $(".same").attr("contentEditable", "false");
    $(this).attr("contentEditable", "true");
});

// 单击文本区的空白区域
$(document).on('click', '.pfread .right', function (e) {
    // 隐藏对话框
    var _con1 = $('#pfread-dialog');
    if (!_con1.is(e.target) && _con1.has(e.target).length === 0) {
        $("#pfread-dialog").offset({top: 0, left: 0});
        $("#pfread-dialog").hide();
    }
    // 取消当前可编辑同文
    var $curSpan = $('.current-span');
    var _con2 = $curSpan;
    if (!_con2.is(e.target) && _con2.has(e.target).length === 0) {
        $curSpan.attr("contentEditable", "false");
        $curSpan.removeClass("current-span");
    }
});

// 滚动文本区滚动条
$('.pfread .right').scroll(function () {
    $("#pfread-dialog").offset({top: 0, left: 0});
    $("#pfread-dialog").hide();
});

// 点击异文选择框的各个选项
$(document).on('click', '#pfread-dialog-base, #pfread-dialog-cmp', function () {
    $('#pfread-dialog-slct').text($(this).text());
});

$(document).on('DOMSubtreeModified', "#pfread-dialog-slct", function() {
    $('.current-not-same').text($(this).text());
    if ($(this).text() === '') {
        $('.current-not-same').addClass('emptyplace');
    } else {
        $('.current-not-same').removeClass('emptyplace');
    }
});

/*-----------导航条----------------*/
// 缩小画布
$(document).on('click', '.btn-reduce', function () {
    if ($.cut.data.ratio > 0.5) {
        $.cut.setRatio($.cut.data.ratio * 0.9);
        highlightBox();
    }
});

// 放大画布
$(document).on('click', '.btn-enlarge', function () {
    if ($.cut.data.ratio < 5) {
        $.cut.setRatio($.cut.data.ratio * 1.5);
        highlightBox();
    }
});

// 显隐所有字框
window.showAllBoxes = function () {
    var $this = $('.btn-cut-show');
    $this.removeClass("btn-cut-show");
    $this.addClass("btn-cut-hidden");
    $.cut.toggleBox(true);
    $.fn.mapKey.bindings = {up: {}, down: {}};
    $.cut.bindKeys();
};
$(document).on('click', '.btn-cut-show', window.showAllBoxes);
$(document).on('click', '.btn-cut-hidden', function () {
    $(this).removeClass("btn-cut-hidden");
    $(this).addClass("btn-cut-show");
    $.cut.toggleBox(false);
    $.fn.mapKey.bindings = {up: {}, down: {}};
    $.cut.bindMatchingKeys();
});

// 显隐字框对应序号
$(document).on('click', '.btn-num-show', function () {
    $(this).removeClass("btn-num-show");
    $(this).addClass("btn-num-hidden");
    showOrder = !showOrder;
    highlightBox();
    $('#order').toggle(showOrder);
});
$(document).on('click', '.btn-num-hidden', function () {
    $(this).removeClass("btn-num-hidden");
    $(this).addClass("btn-num-show");
    showOrder = !showOrder;
    highlightBox();
    $('#order').toggle(showOrder);
});

// 显隐字框对应文本
$(document).on('click', '.btn-txt-show', function () {
    $(this).removeClass("btn-txt-show");
    $(this).addClass("btn-txt-hidden");
    showText = !showText;
    highlightBox();
});
$(document).on('click', '.btn-txt-hidden', function () {
    $(this).removeClass("btn-txt-hidden");
    $(this).addClass("btn-txt-show");
    showText = !showText;
    highlightBox();
});


// 上一条异文
function previousDiff () {
  var current = $('.current-not-same');
  var idx;
  idx = $('.pfread .right .not-same').index(current);
  if (idx < 1) {
      return;
  }
  $('.pfread .right .not-same').eq(idx - 1).click();

}
$(document).on('click', '.btn-previous', previousDiff);
$.mapKey('tab', previousDiff);


// 下一条异文
function nextDiff () {
  var current = $('.current-not-same');
  var idx, $notSame;
  $notSame = $('.pfread .right .not-same');
  idx = $notSame.index(current);
  $notSame.eq(idx + 1).click();
}
$(document).on('click', '.btn-next', nextDiff);
$.mapKey('shift+tab', nextDiff);

// 减少文本字号
$(document).on('click', '.btn-font-reduce', function () {
    var $div = $('.right .sutra-text span');
    var size = parseInt($div.css('font-size'));
    if (size > 8) {
        size--;
        // $('.m-header-font-current').text(size);
        $div.css('font-size', size + 'px');
    }
});

// 增加文本字号
$(document).on('click', '.btn-font-enlarge', function () {
    var $div = $('.right .sutra-text span');
    var size = parseInt($div.css('font-size'));
    if (size < 36) {
        size++;
        // $('.m-header-font-current').text(size);
        $div.css('font-size', size + 'px');
    }
});

// 删除该行
$(document).on('click', '.btn-delete-line', function () {
    var $curSpan = $('.current-span');
    if ($curSpan.length === 0) {
        return showError('提示', '请先在右边文本区点击一行文本，然后重试。');
    }
    var $currentLine = $curSpan.parent(".line");
    $currentLine.fadeOut(500).fadeIn(500);
    if ($currentLine.text().trim() === '') {
        setTimeout(function () {
            $currentLine.remove()
        }, 1100);
    } else {
        setTimeout(function () {
            $currentLine.addClass('delete')
        }, 1100);
    }
});

// 向上增行
$(document).on('click', '.btn-add-up-line', function (e) {
    e.stopPropagation();
    var $curSpan = $('.current-span');
    if ($curSpan.length === 0) {
        return showError('提示', '请先在文本区点选一行文本，然后重试。');
    }
    var $currentLine = $curSpan.parent(".line");
    $curSpan.removeClass("current-span");
    var newline = "<li class='line'><span contentEditable='true' class='same add current-span'></span></li>";
    $currentLine.before(newline);
});

// 向下增行
$(document).on('click', '.btn-add-down-line', function (e) {
    e.stopPropagation();
    var $curSpan = $('.current-span');
    if ($curSpan.length === 0) {
        return showError('提示', '请先在文本区点选一行文本，然后重试。');
    }
    var $currentLine = $curSpan.parent(".line");
    $curSpan.removeClass("current-span");
    var newline = "<li class='line'><span contentEditable='true' class='same add current-span'></span></li>";
    $currentLine.after(newline);
});

// 隐藏异体字
$(document).on('click', '.btn-variants-highlight', function () {
    $('.variant').removeClass("variant-highlight");
    $(this).removeClass("btn-variants-highlight");
    $(this).addClass("btn-variants-normal");
});

// 显示异体字
$(document).on('click', '.btn-variants-normal', function () {
    $('.variant').addClass("variant-highlight");
    $(this).removeClass("btn-variants-normal");
    $(this).addClass("btn-variants-highlight");
});

// 显示空位符
$(document).on('click', '.btn-emptyplaces', function () {
    $('.emptyplace').toggleClass("hidden");
});

// 弹出原文
$(document).on('click', '.btn-txt', function () {
    $('#txtModal').modal();
});

// 帮助
$(document).on('click', '.btn-help', function () {
    window.open('/task/do/proofread/help', '_blank');
});
