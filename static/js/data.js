/*
 * data.js
 *
 * Date: 2019-08-15
 */


// 数据类型
var data_type = location.pathname.split('/')[2];

// 全选
$('#check-all').click(function () {
  var $items = $("tr [type='checkbox']");
  console.log($items.length);
  if (!this.checked)
    $items.removeAttr('checked');
  else
    $items.prop('checked', 'true');
});

// 批量删除
$('#btn-batch-delete').click(function () {
  var args = {
    title: "确定批量删除吗？",
    text: "删除后无法恢复！",
    type: "warning",
    showCancelButton: true,
    confirmButtonColor: "#b8906f",
    confirmButtonText: "确定删除",
    cancelButtonText: "取消",
    closeOnConfirm: false
  };
  var _ids = [];
  $("table tbody input:checkbox:checked").each(function () {
    _ids.push($(this).parents('tr').attr('id'));
  });
  swal(args, function () {
    postApi('/data/' + data_type + '/delete', {data: {_ids: _ids}}, function () {
      showSuccess('删除成功', '数据已删除。');
      setTimeout(function () {
        window.location.reload();
      }, 1500);
    }, function (err) {
      showError('修改失败', err.message);
    });
  });
});

// 删除数据
$('.btn-delete').click(function () {
  var _id = $(this).parents('tr').attr('id');
  var args = {
    title: "确定删除吗？",
    text: "删除后无法恢复！",
    type: "warning",
    showCancelButton: true,
    confirmButtonColor: "#b8906f",
    confirmButtonText: "确定删除",
    cancelButtonText: "取消",
    closeOnConfirm: false
  };
  swal(args, function () {
    postApi('/data/' + data_type + '/delete', {data: {_id: _id}}, function () {
      showSuccess('删除成功', '数据已删除。');
      setTimeout(function () {
        window.location.reload();
      }, 1500);
    }, function (err) {
      showError('修改失败', err.message);
    });
  });
});

// 上传文件-弹框
$('#btn-upload').click(function () {
  $('.modal .uploading .tick').text('');
  $('.modal .uploading').addClass('hide');
  $('.modal .uploaded').addClass('hide');
  $('#uploadModal').modal();
});

// 上传文件-提交
$("#uploadModal #upload_submit").click(function () {
  if (typeof $('#upload')[0].files[0] == "undefined") {
    return showError('请选择文件');
  }
  var file = $('#upload')[0].files[0];
  var regex = /\.(csv|CSV)$/;
  if (!regex.test(file.name)) {
    return showError('文件不是CSV类型');
  }
  if (file.size > (10 * 1024 * 1024)) {
    return showError('文件大小不能超过10M');
  }

  $('.modal .uploading').removeClass('hide');
  setInterval(function () {
    if (!$('.modal .uploading').hasClass('hide')) {
      $('.uploading .tick').text($('.uploading .tick').text() + '·');
    }
  }, 1000);

  var formData = new FormData();
  formData.append('csv', file);
  postFile('/data/' + data_type + '/upload', formData, function (res) {
    $('.modal .uploading').addClass('hide');
    $('.modal .uploaded').removeClass('hide');
    $('.modal .uploaded .message').text(res.data.message);
    if (res.data.errors.length > 0) {
      var $ul = res.data.errors.map(function (error) {
        return "<li><label>" + error[0] + "</label><span>" + error[1][Object.keys(error[1])[0]][1] + "</span></li>";
      }).join('');
      console.log($ul);
      $('.modal .uploaded .errors ul').html($ul);
    }
    $('#upload_submit').addClass('hide');
    $('#confirm').removeClass('hide');
  }, function (err) {
    showError('上传失败', err.message);
  });

  $('#upload_submit').modal('hide');
});

// 上传文件-确定
$('#uploadModal #confirm').click(function () {
  $('#upload_submit').modal('hide');
  window.location.reload();
});

// 搜索
$('#search-input').on("keydown", function (event) {
  var keyCode = event.keyCode || event.which;
  if (keyCode == "13") {
    var q = $(this).val().trim();
    window.location = window.location.pathname + (q === '' ? '' : "?q=" + q);
  }
});