/*
 * task.js
 */

// 领新任务
function pick(url, task_id) {
  var data = {data: task_id === undefined ? {} : {task_id: task_id}};
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
  if (res.code === 3002) {  // error.task_uncompleted
    if (location.pathname.indexOf('/task/do') !== -1)
      window.location = res.url;
    else
      showConfirm("是否继续未完成的任务？", "您还有未完成的任务" + res.doc_id + "，不能领取新任务！", function () {
        window.location = res.url;
      });
  } else if (res.code === 3003) { // error.no_task_to_pick
    showWarning('暂无新任务', res.message);
  } else if (res.code !== 500) {
    showConfirm("是否领取其它任务？", res.message, function () {
      pick("/task/pick/" + taskType);
    });
  } else {
    showError('发生错误', res.message);
  }
}
