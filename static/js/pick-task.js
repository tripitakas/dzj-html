/**
 * 领任务。需提前设置好groupTask变量
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
  if (res.code === 3002) {  // error.task_uncompleted
    if (location.pathname.indexOf('/task/do') !== -1)
      window.location = res.url;
    else
      showConfirm("是否继续未完成的任务？", "您还有未完成的任务" + res.doc_id + "，不能领取新任务！", function () {
        window.location = res.url;
      });
  } else if (res.code === 3003) { // error.no_task_to_pick
    window.location = '/task/lobby/' + groupTask;
  } else if (res.code !== 500) {
    showConfirm("是否领取其它任务？", res.message, function () {
      pick("/task/pick/" + groupTask);
    });
  } else {
    showError('发生错误', res.message);
  }
}
