//popup 类
UM.ui.define('popup', {
    tpl: '<div class="edui-dropdown-menu edui-popup"'+
        '<%if:!${stopprop}%>onmousedown="return false"<%/if%>'+
        '><div class="edui-popup-body" unselectable="on" onmousedown="return false">${subtpl|raw}</div>' +
        '<div class="edui-popup-caret"></div>' +
        '</div>',
    defaultOpt: {
        stopprop:false,
        subtpl: '',
        width: '',
        height: ''
    },
    init: function (options) {
        this.root($(UM.utils.render(this.tpl, options)));
        return this;
    },
    mergeTpl: function (data) {
        return UM.utils.render(this.tpl, {subtpl: data});
    },
    show: function ($obj, posObj) {
        if (!posObj) posObj = {};

        var fnname = posObj.fnname || 'position';
        if (this.trigger('beforeshow') === false) {
            return;
        } else {
            var $root = this.root();
            var rc = $obj[0].getBoundingClientRect();
            var outside = rc.right + $root.width() > $(window).width();
            var top = $obj[fnname]().top + ( posObj.dir == 'right' ? 0 : $obj.outerHeight()) - (posObj.offsetTop || 0);
            var left = $obj[fnname]().left + (posObj.dir == 'right' ? $obj.outerWidth() : 0);
            var rc2 = outside && $obj.parent().parent()[0].getBoundingClientRect();

            $root.css($.extend({display: 'block'}, $obj ? (outside ? {
                top: top,
                right: 0,
                left: 'auto',
                position: 'absolute'
            } : {
                top: top,
                left: left - (posObj.offsetLeft || 0),
                position: 'absolute'
            }) : {}));

            $root.find('.edui-popup-caret').css(outside ? {
                top: posObj.caretTop || 0,
                right: rc2.right - rc.right,
                left: 'auto',
                position: 'absolute'
            } : {
                top: posObj.caretTop || 0,
                left: posObj.caretLeft || 0,
                position: 'absolute'
            }).addClass(posObj.caretDir || "up")

        }
        this.trigger("aftershow");
    },
    hide: function () {
        this.root().css('display', 'none');
        this.trigger('afterhide')
    },
    attachTo: function ($obj, posObj) {
        var me = this
        if (!$obj.data('$mergeObj')) {
            $obj.data('$mergeObj', me.root());
            $obj.on('wrapclick', function (evt) {
                me.show($obj, posObj)
            });
            me.register('click', $obj, function (evt) {
                me.hide()
            });
            me.data('$mergeObj', $obj)
        }
    },
    getBodyContainer: function () {
        return this.root().find(".edui-popup-body");
    }
});