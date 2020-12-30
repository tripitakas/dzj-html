/**
 * 领任务。需设置好taskType变量
 */

// 领新任务
function pick(taskType, task_id) {
  postApi('/task/pick/' + taskType, {task_id: task_id || ''},
      function (res) {
        if (res && res.url)
          window.location = res.url;
      }, function (res) {
        if (res.code === 3002) {  // error.task_uncompleted
          if (location.pathname.indexOf('/task/do') !== -1)
            window.location = res.url;
          else showConfirm("是否继续未完成的任务？",
              "您还有未完成的任务" + (res['doc_id'] || '') + "，不能领取新任务！",
              function () {
                window.location = res.url;
              });
        } else if (res.code === 3003) { // error.no_task_to_pick
          window.location = '/task/lobby/' + taskType;
        } else if (res.code !== 500) {
          showConfirm("是否领取其它任务？", res.message, function () {
            pick(taskType);
          });
        } else {
          showError('发生错误', res.message, 5000);
        }
      }
  );
}
