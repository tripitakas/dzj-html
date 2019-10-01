/*
 * task.js
 *
 * Date: 2019-09-29
 */

// 领取新任务
function pick(url, page_name) {
  var data = {data: page_name === undefined ? {} : {page_name: page_name}};
  postApi(url, data, function (res) {
    if (res && res.url) {
      window.location = res.url;
    }
  }, function (res) {
    error_callback(res);
  });
}

function error_callback(res) {
  console.log(res);
  var task_type = window.location.pathname.split('/')[3];
  var meta = {
    title: "是否继续未完成的任务？",
    text: "您还有未完成的任务" + res.uncompleted_name + "，不能领取新任务！",
    type: "warning",
    showCancelButton: true,
    confirmButtonColor: "#b8906f",
    confirmButtonText: "确定继续",
    cancelButtonText: "取消",
    closeOnConfirm: false
  };
  if (res.code === 3002) {  // error.task_uncompleted
    swal(meta, function () {
      window.location = res.url;
    });
  } else if (res.code === 3003) { // error.no_task_to_pick
    showError('暂无新任务', res.message);
    setTimeout(function () {
      var lobby_type = task_type.indexOf('text_proof') === -1 ? task_type : 'text_proof';
      window.location = "/task/lobby/" + lobby_type;
    }, 1000);
  } else if (res.code !== 500) {
    meta.title = '是否领取其它任务？';
    meta.text = res.message;
    meta.confirmButtonText = '确定领取';
    swal(meta, function () {
      pick("/task/pick/" + task_type);
    });
  } else {
    showError('发生错误', res.message);
  }
}
