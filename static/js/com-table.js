/*
 * com-table.js
 * Date: 2019-08-15
 */

// 排序
$('.sty-table .sort').click(function () {
  var direction = $(this).find('.ion-arrow-down-b').hasClass('toggle') ? '-' : '';
  location.href = setQueryString('order', direction + $(this).attr('title'));
});

// 搜索
$('#search-input').on("keydown", function (event) {
  var keyCode = event.keyCode || event.which;
  if (keyCode === 13) {
    var q = $(this).val().trim();
    location = location.pathname + (q === '' ? '' : "?q=" + q);
  }
});

// 全选
$('#check-all').click(function () {
  var $items = $("tr [type='checkbox']");
  if (!this.checked)
    $items.removeAttr('checked');
  else
    $items.prop('checked', 'true');
});

// 分页-跳转第n页
$('.pagers .page-no').on("keydown", function (event) {
  var keyCode = event.keyCode || event.which;
  if (keyCode === 13) {
    var page = $(this).val().trim();
    page = page > 1 ? page : 1;
    location.href = setQueryString('page', page);
  }
});

// 分页-每页显示n条
$('.pagers .page-size').on("change", function () {
  location.href = setQueryString('page_size', this.value);
});

/*---Modal相关代码---*/
var $modal = $('#dataModal');
var fields = decodeJSON($('#fields').val() || '[]').concat({id: '_id'});

// console.log(fields);

function setModal(modal, info, fields) {
  fields.forEach(function (item) {
    if ('input_type' in item && item['input_type'] === 'radio') {
      if (info[item.id])
        modal.find(':radio[name=' + item.id + '][value=' + info[item.id] + ']').prop('checked', true);
    } else {
      modal.find('.' + item.id).val(info[item.id]);
    }
  })
}

function getModal(modal, fields) {
  var info = {};
  fields.forEach(function (item) {
    if ('input_type' in item && item['input_type'] === 'radio') {
      info[item.id] = modal.find('input:radio[name=' + item.id + ']:checked').val();
      if (!info[item.id])
        info[item.id] = modal.find('.' + item.id + ' :checked').val();
    } else if ('input_type' in item && item['input_type'] === 'checkbox') {
      info[item.id] = $.map(modal.find('.' + item.id + ' :checked'), function (item) {
        return $(item).attr('title');
      });
    } else if ('input_type' in item && item['input_type'] === 'select') {
      info[item.id] = modal.find('.' + item.id + ' :selected').val();
    } else {
      info[item.id] = modal.find('.' + item.id).val();
      if (!info[item.id])
        info[item.id] = modal.find('.' + item.id + ' input').val();
    }
  });
  return info;
}

function resetModal(modal, fields) {
  fields.forEach(function (item) {
    if ('input_type' in item && item['input_type'] === 'radio')
      modal.find('input:radio[name=' + item.id + ']').removeAttr("checked");
    else
      modal.find('.' + item.id).val('');
  });
}

function toggleModal(modal, fields, disabled) {
  disabled = typeof disabled !== 'undefined' && disabled;
  if (disabled) {
    modal.find('.modal-footer').hide();
    fields.forEach(function (item) {
      modal.find('.' + item.id).attr('disabled', 'disabled');
    });
  } else {
    modal.find('.modal-footer').show();
    fields.forEach(function (item) {
      modal.find('.' + item.id).removeAttr('disabled');
    });
  }
}

function getData(id) {
  var data = parseJSON($('#' + id).find('.info').text());
  data['_id'] = id;
  return data;
}

// 新增-弹框
$('.operation #btn-add').click(function () {
  $modal.find('.modal-title').html('新增数据');
  $modal.find('#url').val($(this).attr('url') || location.pathname);
  console.log($(this).attr('url') || location.pathname);
  toggleModal($modal, fields, false);
  resetModal($modal, fields);
  $modal.modal();
});

// 查看-弹框
$('.btn-view').click(function () {
  var id = $(this).parent().parent().attr('id');
  var data = getData(id);
  var title = 'name' in data ? '查看数据 - ' + data.name : '查看数据';
  $modal.find('.modal-title').html(title);
  toggleModal($modal, fields, true);
  setModal($modal, data, fields);
  $modal.modal();
});

// 修改-弹框
$('.btn-update').click(function () {
  var id = $(this).parent().parent().attr('id');
  var data = getData(id);
  var title = 'name' in data ? '修改数据 - ' + data.name : '修改数据';
  $modal.find('#url').val($(this).attr('url') || location.pathname);
  $modal.find('.modal-title').html(title);
  toggleModal($modal, fields, false);
  setModal($modal, data, fields);
  $modal.modal();
});

// 新增/修改-提交
$("#dataModal .modal-confirm").click(function () {
  var data = getModal($modal, fields);
  // console.log(data);
  postApi($modal.find('#url').val().trim(), {data: data}, function () {
    showSuccess('成功', '数据已提交。');
    refresh(1500);
  }, function (error) {
    showError('提交失败', error.message);
  });
});

// 删除
$('.btn-remove').click(function () {
  var id = $(this).parent().parent().attr('id');
  var data = getData(id);
  var name = 'name' in data ? data.name : '';
  var url = $(this).attr('url') || location.pathname + '/delete';
  showConfirm("确定删除" + name + "吗？", "删除后无法恢复！", function () {
    postApi(url, {data: {_id: data._id}}, function () {
      showSuccess('成功', '数据' + name + '已删除');
      refresh(1000);
    }, function (err) {
      showError('删除失败', err.message);
    });
  });
});

// 批量删除
$('#bat-remove').click(function () {
  var ids = $.map($('table tbody :checked'), function (item) {
    return $(item).parent().parent().attr('id');
  });
  if (!ids.length)
    return showWarning('请选择', '当前没有选中任何记录。');
  var url = $(this).attr('url') || location.pathname + '/delete';
  showConfirm("确定批量删除吗？", "删除后无法恢复！", function () {
    postApi(url, {data: {_ids: ids}}, function () {
      showSuccess('删除成功', '数据已删除。');
      refresh(1000);
    }, function (err) {
      showError('删除失败', err.message);
    });
  });
});
