from . import api, view

views = [
    view.TaskLobbyHandler, view.MyTaskHandler, view.PageTaskAdminHandler, view.TaskAdminImageHandler,
    view.PageTaskResumeHandler, view.PageTaskStatisticHandler,
    view.TaskDetailHandler,
]

handlers = [
    api.PublishManyPagesApi, api.PublishImportImageTasksApi, api.RepublishTaskApi,
    api.GetReadyTasksApi, api.AssignTasksApi, api.DeleteTasksApi, api.UpdateTaskApi,
    api.PickTaskApi, api.ReturnTaskApi, api.FinishTaskApi, api.LockTaskDataApi,
    api.UnlockTaskDataApi, api.InitTasksForTestApi,
]
