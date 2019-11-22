/*
 * task.js
 */

// 领新任务
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
  var taskType = window.location.pathname.split('/')[3];
  taskType = taskType.indexOf('text_proof') !== -1 ? 'text_proof' : taskType;
  var meta = {
    type: "warning", title: "是否继续未完成的任务？",
    text: "您还有未完成的任务" + res.doc_id + "，不能领取新任务！",
    showCancelButton: true, closeOnConfirm: false, confirmButtonColor: "#b8906f",
    confirmButtonText: "确定继续", cancelButtonText: "取消"
  };
  if (res.code === 3002) {  // error.task_uncompleted
    if (location.pathname.indexOf('/task/do') !== -1) {
      window.location = res.url;
    } else {
      swal(meta, function () {
        window.location = res.url;
      });
    }
  } else if (res.code === 3003) { // error.no_task_to_pick
    showError('暂无新任务', res.message);
    setTimeout(function () {
      window.location = "/task/lobby/" + taskType;
    }, 1000);
  } else if (res.code !== 500) {
    meta.title = '是否领取其它任务？';
    meta.text = res.message;
    meta.confirmButtonText = '确定领取';
    swal(meta, function () {
      pick("/task/pick/" + taskType);
    });
  } else {
    showError('发生错误', res.message);
  }
}
