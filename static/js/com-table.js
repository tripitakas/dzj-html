/*
 * com-table.js
 * Date: 2019-08-15
 */

// 排序
$('.sty-table .sort').on('click', function () {
  let direction = $(this).find('span').hasClass('icon-triangle-up') ? '-' : '';
  location.href = setQueryString('order', direction + $(this).attr('title').trim());
});

// 过滤
$('.btn-filter').on('click', function () {
  let title = $(this).attr('title').trim();
  location.href = setQueryString(title.split('=')[0], title.split('=')[1])
});

// 搜索
$('#search-input').on("keydown", function (e) {
  let keyCode = e.keyCode || e.which;
  if (keyCode === 13) {
    let q = $(this).val().trim();
    location = location.pathname + (q.length ? '?q=' + q : '');
  }
});

// 全选
$('#check-all').on('click', function () {
  let $items = $("tr [type='checkbox']");
  this.checked ? $items.prop('checked', 'true') : $items.removeAttr('checked');
});

// 列表配置
$('#configModal .modal-confirm').on('click', function () {
  $.map($('#configModal :checkbox(:checked)'), (item) => $('.sty-table .' + $(item).attr('title')).removeClass('hide'));
  $.map($('#configModal :checkbox:not(:checked)'), (item) => $('.sty-table .' + $(item).attr('title')).addClass('hide'));
  let data = {}, key = location.pathname.substr(1).replace(/[\/\-]/g, '_');
  data[key] = $.map($('#configModal :checkbox:not(:checked)'), (item) => $(item).attr('title').trim());
  postApi('/session/config', {data: data});
});


//---Modal相关代码---
function setModal(modal, info, fields) {
  fields.forEach(function (item) {
    if (info[item.id]) { // 如果值为空，则不予设置
      if ('input_type' in item && item['input_type'] === 'radio') {
        modal.find(':radio[name=' + item.id + '][value=' + info[item.id] + ']').prop('checked', true);
      } else if ('input_type' in item && item['input_type'] === 'checkbox') {
        $.map(modal.find('.' + item.id + ' :checkbox'), function (obj) {
          if (info[item.id].indexOf($(obj).attr('title')) !== -1)
            $(obj).prop('checked', true);
          else
            $(obj).removeAttr('checked');
        });
      } else {
        let value = info[item.id];
        value = typeof value === 'object' ? JSON.stringify(value) : value;
        modal.find('.' + item.id).val(value);
      }
    }
  });
}

function getModal(modal, fields) {
  let info = {};
  fields.forEach(function (item) {
    if ('input_type' in item && item['input_type'] === 'checkbox') {
      info[item.id] = $.map(modal.find('.' + item.id + ' :checked'), function (item) {
        return $(item).attr('title');
      });
    } else if ('input_type' in item && item['input_type'] === 'radio') {
      info[item.id] = modal.find('.' + item.id + ' :checked').val();
    } else if ('input_type' in item && item['input_type'] === 'select') {
      info[item.id] = modal.find('.' + item.id + ' :selected').val();
    } else {
      info[item.id] = modal.find('.' + item.id).val();
    }
    if (typeof info[item.id] === 'undefined' || !info[item.id]) {
      delete info[item.id];
    }
  });
  return info;
}

function resetModal(modal, fields) {
  fields.forEach(function (item) {
    if ('input_type' in item && item['input_type'] === 'checkbox') {
      $.map(modal.find('.' + item.id + ' :checked'), function (item) {
        $(item).removeAttr('checked');
      });
    } else if ('input_type' in item && item['input_type'] === 'radio') {
      modal.find('.' + item.id).removeAttr('checked');
    } else if ('input_type' in item && item['input_type'] === 'select') {
      modal.find('.' + item.id + ' :selected').removeAttr('selected');
    } else {
      modal.find('.' + item.id).val('');
    }
  });
}

function toggleModal(modal, fields, disabled) {
  disabled = typeof disabled !== 'undefined' && disabled;
  if (disabled) {
    modal.find('.modal-footer').hide();
    fields.forEach(function (item) {
      modal.find('.' + item.id).attr('disabled', 'disabled');
      modal.find('.' + item.id + ' input').attr('disabled', 'disabled');
    });
  } else {
    modal.find('.modal-footer').show();
    fields.forEach(function (item) {
      modal.find('.' + item.id).removeAttr('disabled');
    });
  }
}

function getData(id) {
  let data = parseJSON($('#' + id).find('.info').text());
  data['_id'] = id;
  return data;
}

let $modal = $('#updateModal');
let fields = decodeJSON($('#updateModal .fields').val() || '[]').concat({id: '_id'});

// 新增-弹框
$('.btn-add').on('click', function () {
  $modal.find('.modal-title').html('新增数据');
  $modal.find('.update-url').val($(this).attr('url') || location.pathname);
  toggleModal($modal, fields, false);
  resetModal($modal, fields);
  $modal.modal();
});

// 查看-弹框
$('.btn-view').on('click', function () {
  let id = $(this).parent().parent().attr('id');
  if ($(this).attr('url')) {
    location.href = $(this).attr('url').replace('@id', id);
  } else {
    let data = getData(id);
    let title = 'name' in data ? '查看数据 - ' + data.name : '查看数据';
    $modal.find('.modal-title').html(title);
    toggleModal($modal, fields, true);
    setModal($modal, data, fields);
    $modal.modal();
  }
});

// 修改-弹框
$('.btn-update').on('click', function () {
  let id = $(this).parent().parent().attr('id');
  let data = getData(id);
  let title = 'name' in data ? '修改数据/' + data.name : '修改数据';
  $modal.find('.update-url').val($(this).attr('url') || location.pathname);
  $modal.find('.modal-title').html(title);
  toggleModal($modal, fields, false);
  setModal($modal, data, fields);
  $modal.modal();
});

// 新增/修改-提交
$("#updateModal .modal-confirm").on('click', function () {
  let data = getModal($modal, fields);
  postApi($modal.find('.update-url').val().trim(), {data: data}, function () {
    showSuccess('成功', '数据已保存', 1000);
    location.reload();
  }, function (error) {
    showError('失败', error.message, 3000);
  });
});

// 删除
$('.btn-remove').on('click', function () {
  let id = $(this).parent().parent().attr('id');
  let data = getData(id);
  let name = 'name' in data ? data.name : '';
  let url = $(this).attr('url') || $(this).attr('title') || location.pathname + '/delete';
  showConfirm("确定删除" + name + "吗？", "删除后无法恢复！", function () {
    postApi(url, {data: {_id: data._id}}, function (res) {
      if (res.count) {
        showSuccess('成功', '数据' + name + '已删除', 1000);
        location.reload();
      } else {
        showError('失败', '数据未删除', 3000);
      }
    }, function (err) {
      showError('失败', err.message, 3000);
    });
  });
});

// 批量删除
$('.operation .bat-remove').on('click', function () {
  let ids = $.map($('table tbody :checked'), (item) => $(item).parent().parent().attr('id'));
  if (!ids.length) return showTips('提示', '当前没有选中任何记录', 3000);
  let url = $(this).attr('url') || $(this).attr('title') || location.pathname + '/delete';
  showConfirm("确定批量删除吗？", "删除后无法恢复！", function () {
    postApi(url, {data: {_ids: ids}}, function (res) {
      if (res.count) {
        showSuccess('成功', '选中' + ids.length + '条记录，已删除' + res.count + '条记录', 1000);
        refresh(1000);
      } else {
        showTips('提示', '删除0条数据', 3000);
      }
    }, function (err) {
      showError('失败', err.message, 3000);
    });
  });
});
