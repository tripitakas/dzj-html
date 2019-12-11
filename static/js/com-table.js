/*
 * com-table.js
 * Date: 2019-08-15
 */

// 排序
$('.sty-table .sort').click(function () {
  var direction = $(this).find('.ion-arrow-down-b').hasClass('toggle') ? '-' : '';
  location = location.pathname + "?order=" + direction + $(this).attr('title');
});

// 搜索
$('#search-input').on("keydown", function (event) {
  var keyCode = event.keyCode || event.which;
  if (keyCode === 13) {
    var q = $(this).val().trim();
    location = location.pathname + (q === '' ? '' : "?q=" + q);
  }
});

// modal相关代码
var $modal = $('#dataModal');
var fields = decodeJSON($('#fields').val()).concat({id: '_id'});
console.log(fields);

function setModal(modal, info, fields) {
  fields.forEach(function (item) {
    console.log(item);
    if ('input_type' in item && item['input_type'] === 'radio')
      modal.find(':radio[name=' + item.id + '][value=' + info[item.id] + ']').prop('checked', true);
    else
      modal.find('.' + item.id).val(info[item.id]);
  })
}

function getModal(modal, fields) {
  var info = {};
  fields.forEach(function (item) {
    if ('input_type' in item && item['input_type'] === 'radio')
      info[item.id] = modal.find('input:radio[name=' + item.id + ']:checked').val();
    else
      info[item.id] = modal.find('.' + item.id).val();
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

function toggleModal(modal, fields, readonly) {
  readonly = typeof readonly !== 'undefined' && readonly;
  if (readonly) {
    modal.find('.modal-footer').hide();
    fields.forEach(function (item) {
      modal.find('.' + item.id).attr('readonly', 'readonly');
    });
  } else {
    modal.find('.modal-footer').show();
    fields.forEach(function (item) {
      modal.find('.' + item.id).removeAttr('readonly');
    });
  }
}

function getData(id) {
  var data = {}, row = $('#' + id);
  fields.forEach(function (item) {
    data[item.id] = row.find('.' + item.id).text();
  });
  data['_id'] = id;
  return data;
}

// 新增-弹框
$('.operation #add').click(function () {
  $modal.find('.modal-title').html('新增数据');
  toggleModal($modal, fields, false);
  resetModal($modal, fields);
  $modal.modal();
});

// 查看-弹框
function view(info) {
  info = typeof info === 'string' ? decodeJSON(info) : info;
  $modal.find('.modal-title').html('查看数据');
  toggleModal($modal, fields, true);
  setModal($modal, info, fields);
  $modal.modal();
}
$('.btn-view').click(function () {
  var rowId = $(this).parent().parent().attr('id');
  var data = getData(rowId);
  console.log(rowId);
  console.log(data);
  view(data);
});

// 修改-弹框
function update(info) {
  info = typeof info === 'string' ? decodeJSON(info) : info;
  $modal.find('.modal-title').html('修改数据');
  toggleModal($modal, fields, false);
  setModal($modal, info, fields);
  $modal.modal();
}
$('.btn-update').click(function () {
  var rowId = $(this).parent().parent().attr('id');
  var data = getData(rowId);
  update(data);
});

// 新增/修改-提交
$("#dataModal .modal-confirm").click(function () {
  var data = getModal($modal, fields);
  postApi(location.pathname, {data: data}, function () {
    showSuccess('成功', '数据已提交。');
    refresh(1500);
  }, function (error) {
    showError('提交失败', error.message);
  });
});

// 删除
function remove(info) {
  info = typeof info === 'string' ? decodeJSON(info) : info;
  var name = 'name' in info ? info.name : '';
  showConfirm("确定删除" + name + "吗？", "删除后无法恢复！", function () {
    postApi(location.pathname + '/delete', {data: {_id: info._id}}, function () {
      showSuccess('成功', '数据' + name + '已删除');
      refresh(1000);
    }, function (err) {
      showError('删除失败', err.message);
    });
  });
}
$('.btn-remove').click(function () {
  var rowId = $(this).parent().parent().attr('id');
  var data = getData(rowId);
  remove(data);
});

// 全选
$('#check-all').click(function () {
  var $items = $("tr [type='checkbox']");
  if (!this.checked)
    $items.removeAttr('checked');
  else
    $items.prop('checked', 'true');
});

// 批量删除
$('#bat-delete').click(function () {
  var ids = $.map($('table tbody :checked'), function (item) {
    return $(item).parents('tr').attr('id');
  });
  if (!ids.length)
    return showWarning('请选择', '当前没有选中任何记录。');

  showConfirm("确定批量删除吗？", "删除后无法恢复！", function () {
    postApi(location.pathname + '/delete', {data: {_ids: ids}}, function () {
      showSuccess('删除成功', '数据已删除。');
      refresh(1000);
    }, function (err) {
      showError('删除失败', err.message);
    });
  });
});

// 上传文件-提交
$("#uploadModal .modal-confirm").click(function () {
  var file = $('#upload')[0].files[0];
  if (typeof file === 'undefined') {
    return showError('请选择文件');
  } else if (!/\.(csv|CSV)$/.test(file.name)) {
    return showError('文件不是CSV类型');
  } else if (file.size > (10 * 1024 * 1024)) {
    return showError('文件大小不能超过10M');
  }

  $('#progress').removeClass('hide');
  var formData = new FormData();
  formData.append('csv', file);
  postFile(location.pathname + '/upload', formData, function (res) {
    $('#progress').addClass('hide');
    var errors = res.data.errors;
    if (errors.length > 0) {
      var text = '<div class="message">' + res.message + '</div><br/><a href="' + res.url + '">下载上传结果</a>';
      showTip('上传完成', text, true);
    } else {
      showTip('上传成功', res.message, true);
    }
  }, function (err) {
    $('#progress').addClass('hide');
    showError('上传失败', err.message);
  });
});
